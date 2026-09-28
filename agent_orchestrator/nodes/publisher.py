"""
AegisForge-AI — Deliverable Publisher Node
============================================
Compiles verified engineering findings into formal tamper-evident documents.

Fix #8:  Reads structured ASME/compliance results from state (last_asme_result,
         last_compliance_result) instead of regex-parsing free conversation text.
Fix #14: Always calls write_sha256_audit_seal — even in the fallback path.
Fix #15: Passes caller="deliverable_publisher" to audit trail.
"""

import datetime
import json
import logging
import re
from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import END
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent_orchestrator.state import AgentState
from agent_orchestrator.models import supervisor_llm, LANGFUSE_CONFIG

logger = logging.getLogger("AegisForge.Publisher")

from tools import (
    doc_generator,
    audit_trail,
    network_verifier,
)

publisher_tools = [
    doc_generator.generate_nfa_documents,
    audit_trail.write_sha256_audit_seal,
    network_verifier.verify_zero_egress,
]

publisher_agent = create_react_agent(
    supervisor_llm,
    tools=publisher_tools,
    prompt=(
        "You are the Sovereign Deliverable Publisher of AegisForge-AI.\n"
        "Your duty is compiling verified engineering findings into formal, tamper-evident documents.\n\n"
        "AVAILABLE TOOLS:\n"
        "1. 'generate_nfa_documents': Injects verified equipment parameters and ASME/compliance "
        "results into official Word/PDF templates.\n"
        "2. 'write_sha256_audit_seal': Hashes generated files and commits an immutable event to "
        "the SQLite cryptographic audit ledger.\n"
        "3. 'verify_zero_egress': Confirms complete air-gapped network isolation.\n\n"
        "EXECUTION INSTRUCTIONS:\n"
        "- Read the full conversation history to extract: equipment_id, ASME results, "
        "compliance verdict, and user-specified names/costs.\n"
        "- CALL 'generate_nfa_documents' with the equipment_id and payload from conversation history.\n"
        "- CALL 'write_sha256_audit_seal' on the generated file.\n"
        "- Report the exact generated file path and SHA-256 seal.\n"
        "- Do NOT invent or hallucinate file paths — only report real artifacts from the tools."
    )
)


def deliverable_publisher_node(
    state: AgentState,
) -> Command[Literal["__end__"]]:

    result = publisher_agent.invoke(state, config=LANGFUSE_CONFIG)
    last_content = result["messages"][-1].content

    # If publisher agent didn't call the tool natively, use structured state (Fix #8)
    if "data/output" not in last_content and ".docx" not in last_content:
        try:
            # --- Read from structured state instead of regex-parsing (Fix #8) ---
            asme = state.get("last_asme_result") or {}
            compliance = state.get("last_compliance_result") or {}
            eq_id = state.get("equipment_id") or "UNKNOWN-VESSEL"

            # Only fall back to regex for equipment_id if not in state
            if eq_id == "UNKNOWN-VESSEL":
                full_history = "\n".join(
                    str(getattr(m, "content", "")) for m in state["messages"]
                )
                m_eq = re.search(r'\b(\d{1,3}-[A-Z]{1,3}-\d{2,4})\b', full_history)
                if m_eq:
                    eq_id = m_eq.group(1)

            now = datetime.datetime.now()
            payload = {
                "equipment_id": eq_id,
                "audit_quarter": f"Q{((now.month - 1) // 3) + 1}-{now.year}",
                "incident_date": now.strftime("%Y-%m-%d"),
                "report_date":   now.strftime("%Y-%m-%d"),
                "valid_until":   (now + datetime.timedelta(days=365)).strftime("%Y-%m-%d"),
            }

            # Read directly from structured ASME result (Fix #8 — no regex parsing)
            if asme:
                payload["t_req_mm"]             = asme.get("t_req_mm")
                payload["measured_thickness_mm"] = asme.get("measured_thickness_mm") or \
                                                   asme.get("t_actual_mm")
                payload["remaining_life_years"]  = asme.get("remaining_life_years")
                payload["status"]               = asme.get("status", "EVALUATED")
                t_req = payload.get("t_req_mm", 0) or 0
                t_act = payload.get("measured_thickness_mm", 0) or 0
                if t_req and t_act:
                    payload["executive_summary"] = (
                        f"Statutory Turnaround Inspection and Wall Thickness Verification "
                        f"for Vessel {eq_id}. Required thickness t_req={t_req:.2f}mm vs "
                        f"measured {t_act:.2f}mm. Integrity status: {payload.get('status', 'EVALUATED')}."
                    )

            # Read compliance result from state
            if compliance:
                payload["compliance_status"] = compliance.get("compliance_status", "")
                payload["sanction_clause"]   = compliance.get("sanction_clause", "")

            doc_res = doc_generator.generate_nfa_documents.invoke({
                "template_type": "ASME_Turnaround_Inspection.docx",
                "base_name":     f"{eq_id}_Statutory_NFA",
                "payload":       payload
            })
            last_content += f"\n\n[PUBLISHED DELIVERABLE]:\n{doc_res}"

            # Fix #14: Always seal — even in fallback path
            try:
                output_path = ""
                if isinstance(doc_res, dict):
                    output_path = doc_res.get("output_path", "")
                elif isinstance(doc_res, str):
                    output_path = doc_res

                if output_path:
                    seal_res = audit_trail.write_sha256_audit_seal.invoke({
                        "file_path":   output_path,
                        "workflow_id": eq_id,
                        "caller":      "deliverable_publisher",   # Fix #15
                    })
                    last_content += f"\n[SHA-256 AUDIT SEAL]: {seal_res}"
            except Exception as seal_err:
                logger.error(f"Audit seal failed: {seal_err}")

        except Exception as e:
            logger.error(f"Publisher fallback error: {e}")

    out_msg = HumanMessage(content=last_content, name="deliverable_publisher")
    return Command(update={"messages": [out_msg]}, goto=END)
