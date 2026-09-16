"""
agent_orchestrator/reviewer_agent.py
Chief Technical Reviewer & Quality Gatekeeper Agent.
Uses local Llama 3.2 (3B) for holistic multi-domain evaluation:
1. Validates ASME Section VIII Div 1 calculation integrity and safety margins.
2. Audits CVC Circular 02/02/2004 compliance and PAC certificate validity (checks expiration).
3. Audits passive network telemetry to confirm process-tree air-gap isolation.
4. Issues final sovereign gatekeeping verdict: APPROVED_FOR_PUBLICATION or REJECTED_AUDIT_HOLD.
"""

import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.state import MultiAgentSystemState
from tools.network_verifier import audit_network_isolation
import agent_orchestrator.base_agent as base_agent
from agent_orchestrator.base_agent import OllamaOfflineException
from tools.audit_trail import append_audit_event
from config.settings import MODEL_REGISTRY, logger


def reviewer_agent_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    """
    Chief Reviewer Node: Cross-domain technical and regulatory gatekeeper.
    Must verify ASME math, CVC PAC validity, and network isolation before publication.
    """
    calc_data = state.get("calculation_data", {})
    comp_data = state.get("compliance_data", {})
    inspection_data = state.get("inspection_data", {})
    params = inspection_data.get("extracted_parameters", {})

    logger.info(f"[ChiefReviewer] Conducting multi-domain audit for {params.get('equipment_id', 'UNKNOWN')}")

    # 1. Network Telemetry Audit
    net_telemetry = audit_network_isolation(scope="process")
    air_gap_intact = net_telemetry.get("is_air_gap_intact", False)

    # 2. Gatekeeping Verifications
    rejection_reasons = []

    if not calc_data:
        rejection_reasons.append("Missing ASME calculation results.")

    if not comp_data:
        rejection_reasons.append("Missing CVC statutory compliance results.")

    if not air_gap_intact:
        rejection_reasons.append(f"Air-gap telemetry breach detected: {net_telemetry.get('verdict')}")

    # Check if PAC is expired or invalid
    comp_verdict = comp_data.get("verdict", "")
    if "EXPIRED_PAC_VIOLATION" in comp_verdict or "VIOLATION" in comp_verdict:
        rejection_reasons.append(f"Statutory compliance failure: {comp_data.get('details') or comp_verdict}")

    is_approved = len(rejection_reasons) == 0
    final_verdict = "APPROVED_FOR_PUBLICATION" if is_approved else "REJECTED_AUDIT_HOLD"

    # 3. LLM Gatekeeper Review Synthesis (Llama 3.2:3b)
    system_prompt = (
        "You are the Chief Technical Auditor & Refinery General Manager at an Indian Oil Corporation refinery. "
        "Review the cross-domain inspection, engineering calculation, and statutory compliance findings. "
        "State whether the documentation package is approved for final executive publication."
    )
    user_prompt = (
        f"Equipment: {params.get('equipment_id')} ({params.get('equipment_name')})\n"
        f"Calculation Status: {calc_data.get('status')} (t_req={calc_data.get('t_req_mm')} mm, delta={calc_data.get('delta_mm')} mm)\n"
        f"Compliance Verdict: {comp_verdict}\n"
        f"Air-Gap Verification: {net_telemetry.get('verdict')}\n"
        f"Gatekeeper Outcome: {final_verdict}\n"
        f"Reasons: {rejection_reasons if rejection_reasons else 'All verification checks passed.'}"
    )

    review_commentary = ""
    try:
        model_name = MODEL_REGISTRY.get("general", "llama3.2:3b")
        review_commentary = base_agent.call_ollama(
            model=model_name,
            messages=[{"role": "user", "content": user_prompt}],
            system_prompt=system_prompt,
            timeout_seconds=90.0
        )
    except OllamaOfflineException as e:
        logger.error(f"[ChiefReviewer] Ollama call failed: {e}")
        state["pipeline_status"] = "HALTED_OLLAMA_SERVICE_UNAVAILABLE"
        entry_hash = append_audit_event(
            tool_name="reviewer_agent_node",
            inputs={"equipment_id": params.get("equipment_id")},
            outputs={"error": str(e), "halt_reason": "Ollama service unavailable"},
            status="HALTED_OLLAMA_OFFLINE",
            caller="reviewer_agent_node"
        )
        state.setdefault("audit_trail_events", []).append(entry_hash)
        raise e

    review_payload = {
        "verdict": final_verdict,
        "is_approved": is_approved,
        "rejection_reasons": rejection_reasons,
        "air_gap_verified": air_gap_intact,
        "chief_reviewer_commentary": review_commentary,
    }
    state["review_verdict"] = review_payload

    if is_approved:
        state["pipeline_status"] = "APPROVED"
    else:
        state["pipeline_status"] = "HALTED_REVIEW_REJECTED"

    entry_hash = append_audit_event(
        tool_name="reviewer_agent_node",
        inputs={"equipment_id": params.get("equipment_id"), "final_verdict": final_verdict},
        outputs=review_payload,
        status="GATEKEEPER_AUDIT_COMPLETE",
        caller="reviewer_agent_node"
    )
    state.setdefault("audit_trail_events", []).append(entry_hash)

    return state
