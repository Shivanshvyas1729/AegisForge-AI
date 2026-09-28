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
        "1. For Python Code / Algorithms / Sandbox Executions:\n"
        "   - Verify the code ran inside the Docker sandbox with exit status 'COMPLETED' or exit 0.\n"
        "   - Report the exact output. Do NOT mention t_req, MAWP, or CVC for code tasks!\n"
        "   - If clean: VERDICT: 'APPROVED'. If errors: VERDICT: 'REJECT'.\n\n"
        "2. For ASME Pressure Vessel Calculations:\n"
        "   - Verify UG-27 t_req, t_actual, safety margin (delta), MAWP, and RSL.\n"
        "   - COMPLIANCE: vessel is ONLY safe if t_actual >= t_req (delta >= 0).\n"
        "   - If t_actual < t_req: issue VERDICT: 'REJECT' — state it's a safety violation.\n"
        "   - If verified: VERDICT: 'APPROVED'.\n\n"
        "3. For Statutory Procurement / Vigilance Audits:\n"
        "   - Verify compliance against CVC guidelines and GFR 2017 rules.\n"
        "   - If verified: VERDICT: 'APPROVED'.\n\n"
        "FORMAL VERDICT STRUCTURE:\n"
        "• VERDICT: 'APPROVED' or 'REJECT'\n"
        "• EXECUTIVE SUMMARY: Concise summary of what was executed and verified.\n"
        "• EXECUTION RESULTS: The actual output or calculation result.\n"
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

    if is_rejected:
        current_retries += 1
        logger.warning(
            f"Chief Reviewer REJECTED output. Retry {current_retries}/{state.get('max_retries', 3)}."
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
    initial_user_msg = ""
    for msg in state["messages"]:
        if isinstance(msg, HumanMessage) and getattr(msg, "name", None) in (None, "user", "Human"):
            initial_user_msg = msg.content
            break
    q_lower = initial_user_msg.lower()
    needs_publishing = any(w in q_lower for w in _PUBLISH_KEYWORDS)

    if not needs_publishing:
        logger.info("Chief Reviewer: Task approved and finalized. Ending pipeline.")
        return Command(update={"messages": [out_msg]}, goto=END)

    logger.info("Chief Reviewer: Task approved. Routing to Deliverable Publisher.")
    return Command(update={"messages": [out_msg]}, goto="deliverable_publisher")
