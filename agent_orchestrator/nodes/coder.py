"""
AegisForge-AI — Coder Agent Node
===================================
Handles ASME calculations, material lookups, API 579 FFS, and Python sandbox.
Stores structured ASME results in state for the publisher to read directly.
"""

import json
import logging
from typing import Literal

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent_orchestrator.state import AgentState
from agent_orchestrator.models import coder_llm, LANGFUSE_CONFIG
from agent_orchestrator.tool_executor import (
    parse_text_tool_call,
    execute_coder_tool,
)

logger = logging.getLogger("AegisForge.Coder")

from tools import (
    asme_calculator,
    api_579_ffs_tool,
    material_lookup_tool,
    docker_sandbox,
)

coder_tools = [
    asme_calculator.calculate_asme_stresses,
    api_579_ffs_tool.run_ffs_assessment,
    material_lookup_tool.lookup_material,
    docker_sandbox.execute_in_sandbox,
]

coder_agent = create_react_agent(
    coder_llm,
    tools=coder_tools,
    prompt=(
        "You are the Senior Scientific Coder Agent of AegisForge-AI, specialized in deterministic "
        "refinery mechanics and secure computing.\n\n"
        "AVAILABLE DETERMINISTIC TOOLS — YOU MUST CALL THEM, NOT DESCRIBE THEM:\n"
        "1. 'calculate_asme_stresses': ASME Section VIII Div 1 UG-27 minimum thickness, MAWP, RSL.\n"
        "2. 'lookup_material': Certified allowable stresses for refinery materials.\n"
        "3. 'run_ffs_assessment': Level 1 Fitness-For-Service RSF under API 579.\n"
        "4. 'execute_in_sandbox': Custom Python algorithms in the secure container.\n\n"
        "MANDATORY TOOL SELECTION RULES:\n"
        "- FOR ASME / UG-27 / WALL THICKNESS: CALL 'calculate_asme_stresses' with all parameters.\n"
        "  NEVER write custom Python for ASME equations — use the certified deterministic tool!\n"
        "- FOR MATERIAL LOOKUPS: CALL 'lookup_material'.\n"
        "- FOR FITNESS-FOR-SERVICE: CALL 'run_ffs_assessment'.\n"
        "- FOR GENERAL CODING (Fibonacci, sorting, data processing, Word docs): CALL 'execute_in_sandbox'.\n"
        "  • SANDBOX RUNTIME: Python 3.9 (Alpine Linux, network-isolated, 256MB RAM).\n"
        "  • INSTALLED PACKAGES: pandas, numpy, python-docx, and Python 3.9 standard library (math, json, re, csv).\n"
        "  • IMPORTS: ALWAYS explicitly import any module you use at the top (e.g. 'import pandas as pd', 'import math'). NEVER use 'pd.' without 'import pandas as pd'.\n"
        "  • MULTIPLE SEQUENCES / UNEQUAL LISTS: If calculating multiple series with different lengths (e.g. Fibonacci numbers up to 10 has 11 elements, Factorials up to 7 has 8 elements), NEVER combine them into a single pd.DataFrame({'Fibonacci': ..., 'Factorial': ...}) as pandas will raise ValueError('All arrays must be of the same length')! Instead, print each sequence clearly under its own heading (e.g. print Fibonacci first, then print Factorials right below it), or create two separate DataFrames.\n"
        "  • SECURITY CONSTRAINTS: Forbidden imports (AST-blocked): 'os', 'sys', 'subprocess', 'shutil', 'socket', 'requests'.\n"
        "  • CODING STANDARDS: Write clean, self-contained Python 3.9 code. NEVER use interactive input() calls.\n"
        "  • PANDAS GUIDELINE: Use modern pandas APIs (never use deprecated/removed 'df.append()'; build DataFrames from a list of dicts: rows.append({...}) then pd.DataFrame(rows), or use pd.concat()).\n"
        "  • Save files to '/output/' inside sandbox.\n"
        "- ALWAYS append '[STATUS: CALCULATION_COMPLETED]' to signal completion."
    )
)


def _get_next_node(state: AgentState, retries: int = 0) -> str:
    if retries >= state.get("max_retries", 3):
        return "human_approval_gate"
    return "supervisor"


def coder_node(
    state: AgentState,
) -> Command[Literal["supervisor", "human_approval_gate"]]:
    """Coder specialist node. Stores ASME results in state for publisher."""
    all_context = " ".join(
        str(getattr(m, "content", "")) for m in state["messages"]
        if hasattr(m, "content") and isinstance(getattr(m, "content", None), str)
    )

    result = coder_agent.invoke(state, config=LANGFUSE_CONFIG)
    result_msgs = result.get("messages", [])
    last_content = str(result_msgs[-1].content) if result_msgs else ""

    tool_was_called = any(isinstance(m, ToolMessage) for m in result_msgs)

    # Extract structured ASME result from ToolMessages if available (Fix #8)
    asme_result = None
    eq_id = state.get("equipment_id")
    for m in result_msgs:
        if isinstance(m, ToolMessage):
            try:
                parsed = json.loads(str(m.content))
                if "t_req_mm" in parsed or "delta_mm" in parsed:
                    asme_result = parsed
                if "equipment_id" in parsed and not eq_id:
                    eq_id = parsed["equipment_id"]
            except Exception:
                pass

    if not tool_was_called:
        tool_name, args = parse_text_tool_call(last_content)
        if tool_name:
            logger.info(f"Coder Node: Intercepting text tool call '{tool_name}' — executing directly")
            tool_result = execute_coder_tool(tool_name, args, all_context)
            last_content = f"Tool '{tool_name}' executed:\n{tool_result}"
            # Try to extract ASME result from inline tool output
            try:
                calc_marker = "[CALCULATION_RESULT]:"
                if calc_marker in tool_result:
                    calc_json_str = tool_result.split(calc_marker, 1)[1].strip()
                    parsed = json.loads(calc_json_str)
                    if "t_req_mm" in parsed or "delta_mm" in parsed:
                        asme_result = parsed
            except Exception:
                pass
        else:
            logger.warning("Coder Node: No native tool call and no parseable text tool call found")

    has_error = any(tag in last_content for tag in ["[STATUS: ERROR]", "Traceback", "[TOOL_ERROR]", "[STATUS: BLOCKED_BY_AST]", "[STATUS: TIMEOUT]"])
    if not has_error and "[STATUS: CALCULATION_COMPLETED]" not in last_content:
        last_content += "\n[STATUS: CALCULATION_COMPLETED]"

    retries = state.get("retry_count", 0)
    if has_error:
        retries += 1
        logger.warning(f"Coder Node execution failed ({retries}/{state.get('max_retries', 3)})")
    elif "[STATUS: CALCULATION_COMPLETED]" in last_content:
        retries = 0

    out_msg = HumanMessage(content=last_content, name="coder_agent")
    update = {
        "messages": [out_msg],
        "retry_count": retries,
    }
    if asme_result:
        update["last_asme_result"] = asme_result
    if eq_id:
        update["equipment_id"] = eq_id

    return Command(update=update, goto=_get_next_node(state, retries))
