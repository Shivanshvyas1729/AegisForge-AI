"""
AegisForge-AI — Reasoning Agent Node
=======================================
Handles statutory compliance, CVC/GFR audits, and RBI score calculation.
Stores structured compliance results in state for the publisher.
"""

import json
import logging
from typing import Literal

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent_orchestrator.state import AgentState
from agent_orchestrator.models import reasoning_llm, LANGFUSE_CONFIG
from agent_orchestrator.tool_executor import (
    parse_text_tool_call,
    execute_reasoning_tool,
)

logger = logging.getLogger("AegisForge.Reasoning")

from tools import (
    compliance_auditor,
    risk_based_inspection_tool,
    routing_guard,
    rag,
)

reasoning_tools = [
    compliance_auditor.audit_mining_compliance,
    compliance_auditor.audit_cvc_compliance,
    risk_based_inspection_tool.calculate_rbi_score,
    routing_guard.verify_routing_policy,
    rag.search_local_knowledge,
]

reasoning_agent = create_react_agent(
    reasoning_llm,
    tools=reasoning_tools,
    prompt=(
        "You are the Senior CMPDI Geospatial & Policy Auditor for AegisForge-Mining (Ministry of Coal / CIL).\n"
        "Your mandate is to evaluate colliery operations, production shortfalls, stripping ratio deviations, "
        "and coal reserve estimates against statutory Coal Mines Regulations (CMR 2017) and CMPDI/UNFC guidelines, "
        "and formulate official, verifiable responses to Parliamentary Questions (PQs) and Ministry Inquiries.\n\n"
        "SUPPORTED STATUTORY FRAMEWORKS:\n"
        "• Coal Mines Regulations 2017 (CMR 2017) — Reg 104 (Opencast Bench Advance), Reg 105 (Dump Slope Stability)\n"
        "• CMPDI Geological Reporting & UNFC Coal Reserves Norms (UNFC-111 Proved, UNFC-122 Indicated)\n"
        "• Ministry of Coal Annual Action Plan (AAP) Production Shortfall Thresholds (> 10% deficit requires explanation)\n"
        "• CIL Subsidiary Performance Mandates (ECL, BCCL, CCL, WCL, SECL, MCL, NCL)\n"
        "• Parliamentary Question (PQ) Response Protocols (Starred/Unstarred Questions)\n\n"
        "AUDIT WORKFLOW — YOU MUST CALL YOUR TOOLS:\n"
        "1. Extract mine_id, subsidiary, planned_production_mt, actual_production_mt, stripping_ratio, or PQ inquiry from context.\n"
        "2. CALL 'audit_mining_compliance' for colliery operational audits or 'search_local_knowledge' for regulatory precedents.\n"
        "3. State clearly whether the operation is 'STATUTORILY COMPLIANT' or 'FLAGGED REGULATORY VIOLATION'.\n"
        "4. Provide actionable remedial measures (e.g. HEMM dragline deployment, bench realignment) and clear PQ answers.\n"
        "5. ALWAYS append '[STATUS: COMPLIANCE_COMPLETED]'."
    )
)



def _get_next_node(state: AgentState) -> str:
    if state.get("retry_count", 0) >= state.get("max_retries", 3):
        return "human_approval_gate"
    return "supervisor"


def reasoning_node(
    state: AgentState,
) -> Command[Literal["supervisor", "human_approval_gate"]]:
    """Reasoning specialist node. Stores compliance results in state."""
    all_context = " ".join(
        str(getattr(m, "content", "")) for m in state["messages"]
        if hasattr(m, "content") and isinstance(getattr(m, "content", None), str)
    )

    result = reasoning_agent.invoke(state, config=LANGFUSE_CONFIG)
    result_msgs = result.get("messages", [])
    last_content = str(result_msgs[-1].content) if result_msgs else ""

    tool_was_called = any(isinstance(m, ToolMessage) for m in result_msgs)

    # Extract structured compliance result from ToolMessages (Fix #8)
    compliance_result = None
    for m in result_msgs:
        if isinstance(m, ToolMessage):
            try:
                parsed = json.loads(str(m.content))
                if "compliance_status" in parsed or "is_compliant" in parsed:
                    compliance_result = parsed
            except Exception:
                pass

    if not tool_was_called:
        tool_name, args = parse_text_tool_call(last_content)
        if tool_name:
            logger.info(f"Reasoning Node: Intercepting text tool call '{tool_name}' — executing directly")
            tool_result = execute_reasoning_tool(tool_name, args, all_context)
            last_content = f"Tool '{tool_name}' executed:\n{tool_result}"
            # Try to extract compliance result from inline output
            try:
                comp_marker = "[COMPLIANCE_RESULT]:"
                if comp_marker in tool_result:
                    comp_json_str = tool_result.split(comp_marker, 1)[1].strip()
                    parsed = json.loads(comp_json_str)
                    if "compliance_status" in parsed or "is_compliant" in parsed:
                        compliance_result = parsed
            except Exception:
                pass
        else:
            logger.warning("Reasoning Node: No native tool call and no parseable text tool call found")

    if "[STATUS: COMPLIANCE_COMPLETED]" not in last_content:
        last_content += "\n[STATUS: COMPLIANCE_COMPLETED]"

    out_msg = HumanMessage(content=last_content, name="reasoning_agent")
    update = {"messages": [out_msg]}
    if compliance_result:
        update["last_compliance_result"] = compliance_result

    return Command(update=update, goto=_get_next_node(state))
