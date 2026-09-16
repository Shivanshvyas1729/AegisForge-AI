"""
agent_orchestrator/workers/compliance_worker.py
Compliance Worker Node.
Enforces statutory procurement integrity under CVC Circular 02/02/2004 and IOCL DoP 4.2.
Strictly respects causal ordering: consumes deterministic calculation_data.
Only authorizes single-source emergency procurement if a physical breach (Delta < 0)
genuinely threatens refinery containment and personnel safety.
"""

import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.state import MultiAgentSystemState
from tools.compliance_auditor import audit_procurement_compliance
import agent_orchestrator.base_agent as base_agent
from agent_orchestrator.base_agent import OllamaOfflineException
from tools.audit_trail import append_audit_event
from config.settings import MODEL_REGISTRY, logger


def compliance_worker_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    """
    Compliance Worker: Audits statutory procurement rules based on calculation findings.
    Ensures CVC emergency exceptions are strictly justified by validated physical breach.
    """
    calc_data = state.get("calculation_data")
    if not calc_data:
        raise ValueError("Causal violation: compliance_worker_node invoked before calculation_data was populated.")

    inspection_data = state.get("inspection_data", {})
    params = inspection_data.get("extracted_parameters", {})

    delta_mm = calc_data.get("delta_mm", 0.0)
    status = calc_data.get("status", "")
    is_breach = delta_mm < 0.0 or "BREACH" in status

    pac_ref = params.get("pac_certificate_ref", "PAC-2026-OEM-V102")
    pac_valid = params.get("pac_valid_until", "2026-12-31")
    cost_inr = float(params.get("estimated_cost_inr", 48500000.0))

    logger.info(f"[ComplianceWorker] Auditing procurement rules. is_breach={is_breach} (delta={delta_mm} mm)")

    # 1. Statutory CVC Tool Audit
    cost_lakhs = round(cost_inr / 100000.0, 2)
    emergency_ref = f"INC-2026-SHUTDOWN-001" if is_breach else None

    # Check for expired PAC certificate
    is_pac_expired = False
    if pac_valid and str(pac_valid) < "2026-01-01":
        is_pac_expired = True

    if is_breach:
        # Physical breach justifies emergency sole-source under CVC 02/02/2004
        compliance_tool_res = audit_procurement_compliance(
            equipment_id=str(params.get("equipment_id", "11-V-102")),
            estimated_cost_lakhs=cost_lakhs,
            is_emergency=True,
            is_single_source=True,
            has_pac=True,
            pac_certificate_ref=pac_ref,
            emergency_justification_ref=emergency_ref,
        )
    else:
        # Safe vessel: emergency single-source is NOT justified under CVC
        compliance_tool_res = audit_procurement_compliance(
            equipment_id=str(params.get("equipment_id", "11-V-102")),
            estimated_cost_lakhs=cost_lakhs,
            is_emergency=False,
            is_single_source=False,
            has_pac=False,
            pac_certificate_ref=None,
            emergency_justification_ref=None,
        )

    # If PAC was expired, override verdict with explicit violation
    if is_pac_expired:
        compliance_tool_res["is_compliant"] = False
        compliance_tool_res["compliance_verdict"] = "EXPIRED_PAC_VIOLATION"
        compliance_tool_res.setdefault("violations", []).append(f"VIOLATION: PAC Certificate expired on {pac_valid}.")

    # Normalize fields for downstream Chief Reviewer
    compliance_tool_res["verdict"] = compliance_tool_res.get("compliance_verdict")
    compliance_tool_res["sanction_authority"] = compliance_tool_res.get("competent_approving_authority")
    compliance_tool_res["cvc_justification_valid"] = compliance_tool_res.get("is_compliant") and is_breach
    compliance_tool_res["is_emergency_justified"] = is_breach

    # 2. Local DeepSeek-R1 Synthesis for formal justification narrative
    system_prompt = (
        "You are an IOCL Senior Vigilance & Contracts Compliance Officer. "
        "Summarize whether single-source emergency procurement under CVC 02/02/2004 and DoP 4.2 "
        "is legally and technically justified given the physical vessel assessment."
    )
    user_prompt = (
        f"Vessel: {params.get('equipment_id')}\n"
        f"Status: {status} (Margin Delta: {delta_mm} mm)\n"
        f"Compliance Audit Verdict: {compliance_tool_res.get('verdict')}\n"
        f"CVC Justification: {compliance_tool_res.get('cvc_justification_valid')}\n"
        f"Sanction Authority: {compliance_tool_res.get('sanction_authority')}"
    )

    narrative_rationale = ""
    try:
        model_name = MODEL_REGISTRY.get("reasoning", "deepseek-r1:1.5b")
        narrative_rationale = base_agent.call_ollama(
            model=model_name,
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            timeout_seconds=90.0
        )
    except OllamaOfflineException as e:
        logger.error(f"[ComplianceWorker] Ollama call failed: {e}")
        state["pipeline_status"] = "HALTED_OLLAMA_SERVICE_UNAVAILABLE"
        entry_hash = append_audit_event(
            tool_name="compliance_worker_node",
            inputs={"equipment_id": params.get("equipment_id")},
            outputs={"error": str(e), "halt_reason": "Ollama service unavailable"},
            status="HALTED_OLLAMA_OFFLINE",
            caller="compliance_worker_node"
        )
        state.setdefault("audit_trail_events", []).append(entry_hash)
        raise e

    compliance_tool_res["narrative_rationale"] = narrative_rationale
    state["compliance_data"] = compliance_tool_res

    entry_hash = append_audit_event(
        tool_name="compliance_worker_node",
        inputs={"equipment_id": params.get("equipment_id"), "is_breach": is_breach},
        outputs={
            "verdict": compliance_tool_res.get("verdict"),
            "sanction_authority": compliance_tool_res.get("sanction_authority"),
            "cvc_justification_valid": compliance_tool_res.get("cvc_justification_valid"),
        },
        status="COMPLIANCE_AUDIT_COMPLETE",
        caller="compliance_worker_node"
    )
    state.setdefault("audit_trail_events", []).append(entry_hash)

    return state
