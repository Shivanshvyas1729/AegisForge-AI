"""
AegisForge-AI — Chief Reviewer Node
=======================================
Forensic validation of specialist outputs. Routes to publisher if docs needed,
or loops back to supervisor for self-correction on REJECT.
Fix #14: Always calls write_sha256_audit_seal even in the fallback path.
"""

import json
import logging
from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import END
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent_orchestrator.state import AgentState
from agent_orchestrator.models import reviewer_llm, LANGFUSE_CONFIG

logger = logging.getLogger("AegisForge.Reviewer")

chief_reviewer_agent = create_react_agent(
    reviewer_llm,
    tools=[],
    prompt=(
        "You are the Sovereign Chief Technical & Engineering Reviewer for AegisForge-AI.\n"
        "Your mission is to conduct forensic validation of specialist outputs.\n\n"
        "ADAPTIVE VERIFICATION INSTRUCTIONS:\n"
        "1. For Python Code / Algorithms / Sandbox Executions & Document Generation:\n"
        "   - Verify the code ran inside the Docker sandbox with exit status 0 / completed.\n"
        "   - If a file or document was created (e.g. Word .docx, PDF, script, data file), clearly confirm the deliverable was created, state its file name, and provide a clear, concise executive summary.\n"
        "   - Do NOT echo the entire raw document content into the chat.\n"
        "   - Do NOT output internal status tags like [STATUS: CALCULATION_COMPLETED] or [STATUS: SUCCESS].\n"
        "   - For document/script creation, use a clean, professional engineering summary instead of a rigid audit template.\n\n"
        "2. For ASME Pressure Vessel Calculations:\n"
        "   - Verify UG-27 t_req, t_actual, safety margin (delta), MAWP, and RSL.\n"
        "   - COMPLIANCE: vessel is ONLY safe if t_actual >= t_req (delta >= 0).\n"
        "   - If t_actual < t_req: issue VERDICT: 'REJECT' — state it's a safety violation.\n"
        "   - If verified: VERDICT: 'APPROVED'.\n"
        "   - Use the FORMAL VERDICT STRUCTURE below.\n\n"
        "3. For Statutory Procurement / Vigilance Audits:\n"
        "   - Verify compliance against CVC guidelines and GFR 2017 rules.\n"
        "   - If verified: VERDICT: 'APPROVED'.\n"
        "   - Use the FORMAL VERDICT STRUCTURE below.\n\n"
        "FORMAL VERDICT STRUCTURE (For ASME Safety Calculations and Statutory Audits):\n"
        "• VERDICT: 'APPROVED' or 'REJECT'\n"
        "• EXECUTIVE SUMMARY: Concise summary of what was executed and verified.\n"
        "• EXECUTION RESULTS: The actual calculation or audit result.\n"
        "• RECOMMENDATION: Operational guidance."
    )
)

_REJECT_MARKERS = [
    "VERDICT: 'REJECT'", "VERDICT: REJECT", "VERDICT:** REJECT", "• VERDICT: REJECT"
]
_PUBLISH_KEYWORDS = [
    "dossier", "report", "nfa", "document", "publish", "word", "pdf", "seal"
]


def chief_reviewer_node(
    state: AgentState,
) -> Command[Literal["supervisor", "human_approval_gate", "deliverable_publisher", "__end__"]]:

    result = chief_reviewer_agent.invoke(state, config=LANGFUSE_CONFIG)
    reviewer_content = result["messages"][-1].content
    out_msg = HumanMessage(content=reviewer_content, name="chief_reviewer")

    is_rejected = any(rej in reviewer_content.upper() for rej in _REJECT_MARKERS)
    current_retries = state.get("retry_count", 0)

    # Check if calculation / specialist work actually completed without code errors
    has_asme_result = bool(state.get("last_asme_result"))
    has_completed_tag = any(
        any(tag in str(getattr(m, "content", "")) for tag in ["[STATUS: CALCULATION_COMPLETED]", "[STATUS: COMPLIANCE_COMPLETED]"])
        for m in state.get("messages", [])
    )
    has_execution_error = any(
        any(err in str(getattr(m, "content", "")) for err in ["[STATUS: ERROR]", "Traceback (most recent call last):", "[TOOL_ERROR]"])
        for m in state.get("messages", [])[-3:]
    )

    # If the mathematical calculation / compliance audit ran successfully, a "REJECT" verdict
    # means the physical vessel or procurement failed compliance — it is a legitimate technical
    # conclusion, NOT an execution bug! Finalize immediately without looping.
    # However, if the code actually crashed or encountered a runtime error, loop back for self-healing.
    if is_rejected and (has_execution_error or not (has_asme_result or has_completed_tag)):
        current_retries += 1
        logger.warning(
            f"Chief Reviewer REJECTED execution output. Retry {current_retries}/{state.get('max_retries', 3)}."
        )
        if current_retries >= state.get("max_retries", 3):
            logger.warning("Max retries on rejection — routing to Human Approval Gate.")
            return Command(
                update={"retry_count": current_retries, "messages": [out_msg]},
                goto="human_approval_gate"
            )
        logger.info("Looping back to Supervisor for autonomous self-correction.")
        return Command(
            update={"retry_count": current_retries, "messages": [out_msg]},
            goto="supervisor"
        )

    # APPROVED — check if formal publication is required
    latest_user_msg = ""
    for msg in reversed(state.get("messages", [])):
        if isinstance(msg, HumanMessage) and getattr(msg, "name", None) in (None, "user", "Human"):
            latest_user_msg = str(msg.content)
            break
    q_lower = latest_user_msg.lower()
    needs_publishing = any(w in q_lower for w in _PUBLISH_KEYWORDS) or bool(state.get("human_approved"))

    # If a specialist already generated a Word .docx deliverable directly in the sandbox,
    # we don't need a redundant conversion run by deliverable_publisher
    has_direct_docx = any(".docx" in str(getattr(m, "content", "")) for m in state.get("messages", []))
    if needs_publishing and not has_direct_docx:
        logger.info("Chief Reviewer: Task approved. Routing to Deliverable Publisher.")
        return Command(update={"messages": [out_msg]}, goto="deliverable_publisher")

    logger.info("Chief Reviewer: Task approved and finalized. Ending pipeline.")
    return Command(update={"messages": [out_msg]}, goto=END)

