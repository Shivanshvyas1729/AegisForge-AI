"""
AegisForge-AI — Vision Agent Node
===================================
Handles OCR extraction from PDFs, P&IDs, inspection photos, UT grids.
"""

import logging
from typing import Literal

from langchain_core.messages import HumanMessage, ToolMessage
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent_orchestrator.state import AgentState
from agent_orchestrator.models import vision_llm, LANGFUSE_CONFIG
from agent_orchestrator.tool_executor import parse_text_tool_call, execute_vision_tool

logger = logging.getLogger("AegisForge.Vision")

from tools import (
    geological_extractor_tool,
    production_grid_analyzer,
    topic_modeler,
    inspection_extractor_tool,
    thickness_grid_analyzer,
    file_io,
)

vision_tools = [
    geological_extractor_tool.extract_geological_data,
    production_grid_analyzer.analyze_production_grid,
    topic_modeler.generate_topic_cloud_and_themes,
    inspection_extractor_tool.extract_inspection_data,
    thickness_grid_analyzer.analyze_thickness_grid,
    file_io.read_scanned_pdf,
]

vision_agent = create_react_agent(
    vision_llm,
    tools=vision_tools,
    prompt=(
        "You are the Lead Vision & Geological Document Intelligence Agent for AegisForge-Mining (Ministry of Coal / CMPDI).\n"
        "Your mission is to extract structured geological, borehole, stratigraphical, production, and topic data "
        "from ANY user-provided borehole lithology log, drill core record, mine production spreadsheet, or exploration dossier.\n\n"
        "HANDLING USER DOCUMENTS:\n"
        "- Inspect the user query and message history for target file paths (e.g. in 'data/', 'data/uploads/', 'sample_data/').\n"
        "- Use 'extract_geological_data' for scanned borehole logs, core strata charts, and geological PDFs/images.\n"
        "- Use 'analyze_production_grid' for monthly coal production and overburden removal spreadsheets (.csv, .xlsx).\n"
        "- Use 'generate_topic_cloud_and_themes' for extracting recurring themes and generating word clouds from exploration dossiers.\n\n"
        "DYNAMIC EXTRACTION TARGETS:\n"
        "• Borehole ID / Drillhole Number (e.g., BH-01, CMPDI-DH-42)\n"
        "• Seam Name / Coal Horizon (e.g., Seam IV, Barakar Top)\n"
        "• Seam Thickness (m) & Total Borehole Depth (m)\n"
        "• Overburden Thickness (m) & Parting (m)\n"
        "• Ash Content %, Moisture %, and Gross Calorific Value (GCV)\n"
        "• Formation (Barakar Formation, Raniganj Formation, Damuda Group)\n"
        "• Subsidiary / Coalfield (CMPDI, ECL, BCCL, CCL, WCL, SECL, MCL, NCL)\n\n"
        "MANDATORY: You MUST call one of your tools. Do not describe what you would do — call the tool.\n"
        "When extraction is complete, present the extracted data clearly and append '[STATUS: EXTRACTION_COMPLETED]'."
    )
)



def _get_next_node(state: AgentState, default: str) -> str:
    if state.get("retry_count", 0) >= state.get("max_retries", 3):
        return "human_approval_gate"
    return "supervisor"


def vision_node(
    state: AgentState,
) -> Command[Literal["supervisor", "human_approval_gate"]]:
    """Vision specialist node with text tool-call fallback."""
    result = vision_agent.invoke(state, config=LANGFUSE_CONFIG)
    result_msgs = result.get("messages", [])
    last_content = str(result_msgs[-1].content) if result_msgs else ""

    tool_was_called = any(isinstance(m, ToolMessage) for m in result_msgs)

    if not tool_was_called:
        tool_name, args = parse_text_tool_call(last_content)
        if tool_name:
            logger.info(f"Vision Node: Intercepting text tool call '{tool_name}' — executing directly")
            tool_result = execute_vision_tool(tool_name, args)
            last_content = f"Tool '{tool_name}' executed:\n{tool_result}"
        else:
            logger.warning("Vision Node: No native tool call and no parseable text tool call found")

    if "[STATUS: EXTRACTION_COMPLETED]" not in last_content:
        last_content += "\n[STATUS: EXTRACTION_COMPLETED]"

    out_msg = HumanMessage(content=last_content, name="vision_agent")
    return Command(
        update={"messages": [out_msg]},
        goto=_get_next_node(state, "supervisor")
    )
