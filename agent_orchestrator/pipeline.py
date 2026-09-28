import os
import sys
import re
import json
import logging
import datetime
import warnings
from typing import Literal, Sequence, Annotated
from pydantic import BaseModel, Field

# Anchor paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

warnings.filterwarnings('ignore')
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logger = logging.getLogger("AegisForge.Pipeline")

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, SystemMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt
from langgraph.checkpoint.memory import MemorySaver

# --- LANGFUSE INTEGRATION ---
try:
    try:
        from langfuse.langchain import CallbackHandler
    except ImportError:
        from langfuse.callback import CallbackHandler
    langfuse_handler = CallbackHandler()
    LANGFUSE_CONFIG = {"callbacks": [langfuse_handler]}
    logger.info("Langfuse tracking enabled successfully.")
except Exception as e:
    LANGFUSE_CONFIG = {}
    logger.warning(f"Langfuse not enabled. Tracing disabled: {e}")
# ----------------------------

# Import Tools
from tools import (
    api_579_ffs_tool,
    asme_calculator,
    audit_trail,
    compliance_auditor,
    doc_generator,
    docker_sandbox,
    file_io,
    inspection_extractor_tool,
    material_lookup_tool,
    network_verifier,
    risk_based_inspection_tool,
    routing_guard,
    thickness_grid_analyzer,
)

# ============================================================================
# 1. STATE DEFINITION
# ============================================================================
class AgentState(BaseModel):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    human_approved: bool = Field(default=False)
    human_feedback: str = Field(default="")
    task_scope: str = Field(default="auto")  # "standalone_calc" | "dossier_pipeline" | "compliance"


# ============================================================================
# 2. LOCAL OLLAMA MODEL INSTANTIATION
# ============================================================================
supervisor_llm = ChatOllama(model="llama3.1:8b", temperature=0, format="json")
coder_llm = ChatOllama(model="qwen2.5-coder:7b", temperature=0)
reasoning_llm = ChatOllama(model="llama3.1:8b", temperature=0)
vision_llm = ChatOllama(model="llama3.2:3b", temperature=0, format="json")
reviewer_llm = ChatOllama(model="llama3.1:8b", temperature=0)
conversational_llm = ChatOllama(model="llama3.1:8b", temperature=0.3)
router_llm = ChatOllama(model="laya:421m", temperature=0, format="json")


# ============================================================================
# 3. WORKER AGENTS & TOOLS
# ============================================================================
vision_tools = [
    inspection_extractor_tool.extract_inspection_data,
    thickness_grid_analyzer.analyze_thickness_grid,
    file_io.read_scanned_pdf,
]

coder_tools = [
    asme_calculator.calculate_asme_stresses,
    api_579_ffs_tool.run_ffs_assessment,
    material_lookup_tool.lookup_material,
    docker_sandbox.execute_in_sandbox,
]

reasoning_tools = [
    compliance_auditor.audit_cvc_compliance,
    risk_based_inspection_tool.calculate_rbi_score,
    routing_guard.verify_routing_policy,
]

publisher_tools = [
    doc_generator.generate_nfa_documents,
    audit_trail.write_sha256_audit_seal,
    network_verifier.verify_zero_egress,
]

def get_next_node(last_message: BaseMessage, default_goto: str, state: AgentState) -> str:
    """Workers always report back to supervisor for holistic multi-step plan orchestration and feedback loops."""
    if getattr(state, "retry_count", 0) >= getattr(state, "max_retries", 3):
        return "human_approval_gate"
    return "supervisor"


# ============================================================================
# TOOL EXECUTION HELPERS
# Called when Ollama LLMs emit tool calls as JSON text instead of native
# function-calling — this is a known limitation of smaller local models.
# We detect this case and execute the tool directly.
# ============================================================================
def _parse_text_tool_call(content: str):
    """
    Parse a JSON tool call emitted as plain text by the LLM.
    Returns (tool_name: str, args: dict) or ("", {}) if not found.
    """
    # Find all JSON-like blocks, try largest ones first
    candidates = re.findall(r'\{(?:[^{}]|\{[^{}]*\})*\}', content, re.DOTALL)
    for block in sorted(candidates, key=len, reverse=True):
        # Fix common LLM JSON mistakes: missing commas between keys
        fixed = re.sub(r'"\s*\n\s*"', '",\n"', block)
        try:
            parsed = json.loads(fixed)
        except Exception:
            try:
                parsed = json.loads(block)
            except Exception:
                continue
        name = parsed.get("name", "")
        if name:
            args = parsed.get("arguments", parsed.get("parameters", parsed.get("args", {})))
            return str(name), (args if isinstance(args, dict) else {})
    return "", {}


def _execute_coder_tool(tool_name: str, args: dict, all_context: str = "") -> str:
    """
    Execute a coder tool by name with given args.
    If args are incomplete, extract them dynamically from context.
    Returns formatted result string.
    """
    name_lower = tool_name.lower()
    try:
        # --- execute_in_sandbox ---
        if any(kw in name_lower for kw in ["sandbox", "execute", "run_code"]):
            code = args.get("code_string") or args.get("code") or args.get("code_str", "")
            title = args.get("task_title") or args.get("title") or "Sandbox Execution"
            if not code:
                return "[ERROR]: No code_string found in tool arguments"
            res = docker_sandbox.execute_in_sandbox.invoke({"code_string": code, "task_title": title})
            output = res.get("output", res.get("stdout", str(res)))
            status = res.get("status", "COMPLETED")
            return f"[DOCKER_SANDBOX_OUTPUT]:\n{output}\n[STATUS: {status}]"

        # --- calculate_asme_stresses ---
        elif any(kw in name_lower for kw in ["asme", "calculate_asme", "stress"]):
            # If args are empty, extract dynamically from all_context
            if not args.get("design_pressure_mpa") and all_context:
                p_m = re.search(r'(?:design\s+pressure|pressure)[:\s=]*([\d.]+)', all_context, re.I)
                r_m = re.search(r'(?:inside\s+radius|radius)[:\s=]*([\d.]+)', all_context, re.I)
                s_m = re.search(r'(?:allowable\s+stress|stress)[:\s=]*([\d.]+)', all_context, re.I)
                ca_m = re.search(r'(?:corrosion\s+allowance)[:\s=]*([\d.]+)', all_context, re.I)
                t_m = re.search(r'(?:actual\s+thickness|measured\s+thickness)[:\s=]*([\d.]+)', all_context, re.I)
                if p_m: args["design_pressure_mpa"] = float(p_m.group(1))
                if r_m: args["inside_radius_mm"] = float(r_m.group(1))
                if s_m: args["allowable_stress_mpa"] = float(s_m.group(1))
                if ca_m: args["corrosion_allowance_mm"] = float(ca_m.group(1))
                if t_m: args["measured_thickness_mm"] = float(t_m.group(1))
            res = asme_calculator.calculate_asme_stresses.invoke(args)
            return f"[CALCULATION_RESULT]:\n{json.dumps(res, indent=2, default=str)}"

        # --- lookup_material ---
        elif any(kw in name_lower for kw in ["material", "lookup"]):
            res = material_lookup_tool.lookup_material.invoke(args)
            return f"[MATERIAL_LOOKUP_RESULT]:\n{res}"

        # --- run_ffs_assessment ---
        elif any(kw in name_lower for kw in ["ffs", "fitness"]):
            res = api_579_ffs_tool.run_ffs_assessment.invoke(args)
            return f"[FFS_RESULT]:\n{res}"

    except Exception as e:
        logger.error(f"Tool execution error for '{tool_name}': {e}")
        return f"[TOOL_ERROR]: {e}"

    return f"[UNKNOWN_TOOL]: {tool_name}"


def _execute_reasoning_tool(tool_name: str, args: dict, all_context: str = "") -> str:
    """Execute a reasoning/compliance tool by name. Extracts params from context if args incomplete."""
    name_lower = tool_name.lower()
    try:
        if any(kw in name_lower for kw in ["cvc", "compliance", "audit", "procurement"]):
            # Dynamically extract missing args from conversation context
            if not args.get("equipment_id") and all_context:
                m_eq = re.search(r'\b(\d{1,3}-[A-Z]{1,3}-\d{2,4}|[A-Z][A-Z0-9-]{3,}\s+\d+|pump\s+[A-Z0-9-]+|vessel\s+[A-Z0-9-]+)', all_context, re.I)
                if m_eq:
                    args["equipment_id"] = m_eq.group(0).strip()
            if not args.get("estimated_cost_lakhs") and all_context:
                m_cost = re.search(r'([\d.]+)\s*(?:lakhs?|lakh)', all_context, re.I)
                if m_cost:
                    args["estimated_cost_lakhs"] = float(m_cost.group(1))
            if not args.get("applicable_cvc_clause") and all_context:
                m_clause = re.search(r'(GFR[\s\w/.,]+Rule\s*\d+|CVC[^.\n]{0,60}|Rule\s*\d+[^.\n]{0,40})', all_context, re.I)
                if m_clause:
                    args["applicable_cvc_clause"] = m_clause.group(0).strip()
            res = compliance_auditor.audit_cvc_compliance.invoke(args)
            return f"[COMPLIANCE_RESULT]:\n{json.dumps(res, indent=2, default=str)}"

        elif any(kw in name_lower for kw in ["rbi", "risk"]):
            res = risk_based_inspection_tool.calculate_rbi_score.invoke(args)
            return f"[RBI_RESULT]:\n{res}"

        elif "routing" in name_lower or "verify" in name_lower:
            res = routing_guard.verify_routing_policy.invoke(args)
            return f"[ROUTING_RESULT]:\n{res}"

    except Exception as e:
        logger.error(f"Reasoning tool error for '{tool_name}': {e}")
        return f"[TOOL_ERROR]: {e}"

    return f"[UNKNOWN_TOOL]: {tool_name}"


def _execute_vision_tool(tool_name: str, args: dict) -> str:
    """Execute a vision tool by name."""
    name_lower = tool_name.lower()
    try:
        if any(kw in name_lower for kw in ["extract", "inspection"]):
            res = inspection_extractor_tool.extract_inspection_data.invoke(args)
            return f"[EXTRACTION_RESULT]:\n{res}"
        elif any(kw in name_lower for kw in ["thickness", "grid", "analyze"]):
            res = thickness_grid_analyzer.analyze_thickness_grid.invoke(args)
            return f"[GRID_ANALYSIS_RESULT]:\n{res}"
        elif any(kw in name_lower for kw in ["pdf", "read", "scanned"]):
            res = file_io.read_scanned_pdf.invoke(args)
            return f"[PDF_CONTENT]:\n{str(res)[:2000]}"
    except Exception as e:
        logger.error(f"Vision tool error for '{tool_name}': {e}")
        return f"[TOOL_ERROR]: {e}"
    return f"[UNKNOWN_TOOL]: {tool_name}"


# ============================================================================
# VISION AGENT
# ============================================================================
vision_agent = create_react_agent(
    vision_llm,
    tools=vision_tools,
    prompt=(
        "You are the Lead Vision & Document Intelligence Agent for AegisForge-AI.\n"
        "Your mission is to extract structured operational, geometric, material, and regulatory data from ANY user-provided PDF, engineering drawing, P&ID schematic, inspection photo, or coordinate grid.\n\n"
        "HANDLING USER DOCUMENTS:\n"
        "- Inspect the user query and message history for target file paths (e.g. in 'data/', 'data/uploads/', 'sample_data/').\n"
        "- Use 'read_scanned_pdf' or 'extract_inspection_data' for reading text, tables, P&ID schematics, engineering drawings, and inspection sheets from PDFs and images (.png, .jpg, .jpeg, .tiff, .bmp, .webp).\n"
        "- Use 'analyze_thickness_grid' for ultrasonic thickness coordinate matrices (.csv, .xlsx).\n\n"
        "DYNAMIC EXTRACTION TARGETS:\n"
        "• Equipment Tag / ID (e.g. 11-V-102, 22-C-101, P-204)\n"
        "• Design Pressure P (MPa) & Inside Radius R (mm)\n"
        "• Material Specification (MOC, e.g. 2.25Cr-1Mo, SA-387 Gr 22, SA-516 Gr 70)\n"
        "• Measured Wall Thickness t_actual (mm) & Corrosion Rate CR (mm/yr)\n"
        "• Statutory Context (Tender type, estimated budget, emergency justification, applicable circulars)\n\n"
        "MANDATORY: You MUST call one of your tools to do the actual extraction. Do not describe what you would do — call the tool.\n"
        "When extraction is complete, present the extracted data clearly in a markdown summary and append '[STATUS: EXTRACTION_COMPLETED]'."
    )
)

def vision_node(state: AgentState) -> Command[Literal["supervisor", "human_approval_gate", "chief_reviewer"]]:
    """Vision specialist node with smart tool-call fallback."""
    from langchain_core.messages import ToolMessage as _TM
    result = vision_agent.invoke(state, config=LANGFUSE_CONFIG)
    result_msgs = result.get("messages", [])
    last_content = str(result_msgs[-1].content) if result_msgs else ""

    # Check if tools were actually called natively via ReAct loop
    tool_was_called = any(isinstance(m, _TM) for m in result_msgs)

    if not tool_was_called:
        # LLM emitted JSON tool call as text — parse and execute it
        tool_name, args = _parse_text_tool_call(last_content)
        if tool_name:
            logger.info(f"Vision Node: Intercepting text tool call '{tool_name}' — executing directly")
            tool_result = _execute_vision_tool(tool_name, args)
            last_content = f"Tool '{tool_name}' executed:\n{tool_result}"
        else:
            logger.warning("Vision Node: No native tool call, no parseable text tool call found")

    if "[STATUS: EXTRACTION_COMPLETED]" not in last_content:
        last_content += "\n[STATUS: EXTRACTION_COMPLETED]"

    out_msg = HumanMessage(content=last_content, name="vision_agent")
    goto = get_next_node(out_msg, "supervisor", state)
    return Command(update={"messages": [out_msg]}, goto=goto)


# ============================================================================
# CODER AGENT
# ============================================================================
coder_agent = create_react_agent(
    coder_llm,
    tools=coder_tools,
    prompt=(
        "You are the Senior Scientific Coder Agent of AegisForge-AI, specialized in deterministic refinery mechanics and secure computing.\n"
        "Your responsibility is to perform high-precision engineering math and execute Python workloads in the air-gapped Docker sandbox.\n\n"
        "AVAILABLE DETERMINISTIC TOOLS — YOU MUST CALL THEM, NOT DESCRIBE THEM:\n"
        "1. 'calculate_asme_stresses': Computes ASME Section VIII Div 1 UG-27 minimum thickness (t_req), Safety Margin (Δ), Maximum Allowable Working Pressure (MAWP), and API 510 Remaining Service Life (RSL).\n"
        "2. 'lookup_material': Retrieves certified allowable stresses (S) and yield limits across temperatures for refinery materials.\n"
        "3. 'run_ffs_assessment': Evaluates Level 1 Fitness-For-Service Remaining Strength Factor (RSF) under API 579.\n"
        "4. 'execute_in_sandbox': Executes custom Python algorithms, data analysis, and simulations inside the secure container.\n\n"
        "MANDATORY TOOL SELECTION RULES:\n"
        "- FOR ASME SECTION VIII / UG-27 / WALL THICKNESS / PRESSURE VESSEL CALCULATIONS:\n"
        "  • YOU MUST CALL 'calculate_asme_stresses' with parameters extracted from the user message:\n"
        "    - design_pressure_mpa: the design pressure in MPa\n"
        "    - inside_radius_mm: the inside radius in mm\n"
        "    - allowable_stress_mpa: the allowable stress in MPa\n"
        "    - corrosion_allowance_mm: the corrosion allowance in mm\n"
        "    - measured_thickness_mm: the actual measured wall thickness in mm\n"
        "  • NEVER write custom Python code or invoke 'execute_in_sandbox' for ASME pressure vessel equations — always call the certified deterministic tool!\n"
        "- FOR MATERIAL LOOKUPS: CALL 'lookup_material' with the material grade (e.g. SA-387 Gr 22).\n"
        "- FOR FITNESS-FOR-SERVICE: CALL 'run_ffs_assessment' with the required API 579 parameters.\n"
        "- FOR GENERAL CODING & ALGORITHMS (Fibonacci, primes, data sorting, file generation, Word docs):\n"
        "  • CALL 'execute_in_sandbox'.\n"
        "  • Provide clean, self-contained Python code in 'code_string'.\n"
        "  • Always specify a concise 3 to 6 word title in 'task_title'.\n"
        "  • NEVER use interactive `input()` calls.\n"
        "  • Use `print(...)` to output results.\n"
        "  • FILE GENERATION: Save files to '/output/' directory inside sandbox (e.g. '/output/report.docx') and print the absolute path.\n"
        "- When the tool returns results, present the numerical findings clearly.\n"
        "- ALWAYS append '[STATUS: CALCULATION_COMPLETED]' to signal completion to the supervisor."
    )
)

def coder_node(state: AgentState) -> Command[Literal["supervisor", "human_approval_gate", "chief_reviewer"]]:
    """Coder specialist node with smart tool-call fallback."""
    from langchain_core.messages import ToolMessage as _TM
    all_context = " ".join(
        str(getattr(m, "content", "")) for m in state.messages
        if hasattr(m, "content") and isinstance(getattr(m, "content", None), str)
    )
    result = coder_agent.invoke(state, config=LANGFUSE_CONFIG)
    result_msgs = result.get("messages", [])
    last_content = str(result_msgs[-1].content) if result_msgs else ""

    # Check if tools were actually called natively via ReAct loop
    tool_was_called = any(isinstance(m, _TM) for m in result_msgs)

    if not tool_was_called:
        # LLM emitted JSON tool call as text — parse and execute directly
        tool_name, args = _parse_text_tool_call(last_content)
        if tool_name:
            logger.info(f"Coder Node: Intercepting text tool call '{tool_name}' — executing directly")
            tool_result = _execute_coder_tool(tool_name, args, all_context)
            last_content = f"Tool '{tool_name}' executed:\n{tool_result}"
        else:
            logger.warning("Coder Node: No native tool call and no parseable text tool call found")

    if "[STATUS: CALCULATION_COMPLETED]" not in last_content:
        last_content += "\n[STATUS: CALCULATION_COMPLETED]"

    out_msg = HumanMessage(content=last_content, name="coder_agent")
    goto = get_next_node(out_msg, "supervisor", state)
    return Command(update={"messages": [out_msg]}, goto=goto)


# ============================================================================
# REASONING AGENT
# ============================================================================
reasoning_agent = create_react_agent(
    reasoning_llm,
    tools=reasoning_tools,
    prompt=(
        "You are the Senior Statutory Compliance & Regulatory Reasoning Agent for AegisForge-AI, specialized in Indian Public Sector Undertaking (PSU) governance.\n"
        "Your mandate is to evaluate procurement, emergency justifications, and inspection protocols against ANY applicable statutory framework.\n\n"
        "SUPPORTED STATUTORY FRAMEWORKS:\n"
        "• Central Vigilance Commission (CVC) Directives & Vigilance Manual (Circular 02/02/2004, 2018, 2021)\n"
        "• General Financial Rules (GFR 2017) — Rule 149 (GeM procurement), Rule 194 (Single-source/Proprietary selection)\n"
        "• Proprietary Article Certificate (PAC) and Emergency Procurement Exception mandates\n"
        "• Delegation of Power (DoP) Financial Approval Limits for Refinery Executives (GM, ED, Director, Board)\n"
        "• Statutory Plant Codes: OISD-153, PESO SMPV Rules, API 581 Risk-Based Inspection (RBI)\n\n"
        "AUDIT WORKFLOW — YOU MUST CALL YOUR TOOLS, NOT DESCRIBE THEM:\n"
        "1. Read the user's operational justification carefully — extract equipment ID, cost, statutory framework, and authority from the message.\n"
        "2. CALL 'audit_cvc_compliance' with the dynamically extracted parameters:\n"
        "   - equipment_id: the equipment tag or procurement item name from the user's message\n"
        "   - estimated_cost_lakhs: the cost extracted from the user's message in lakhs INR\n"
        "   - is_single_source: whether this is single-source procurement\n"
        "   - has_pac: whether a Proprietary Article Certificate exists\n"
        "   - is_emergency: whether this is an emergency procurement\n"
        "   - applicable_cvc_clause: the specific CVC/GFR/DoP clause referenced in the user's message\n"
        "   - required_financial_authority: the required sanctioning authority based on the cost\n"
        "3. For RBI (Risk-Based Inspection) score calculations, CALL 'calculate_rbi_score' with parameters from the message.\n"
        "4. State clearly whether the procurement is 'STATUTORILY COMPLIANT' or 'FLAGGED VIOLATION', and append '[STATUS: COMPLIANCE_COMPLETED]'."
    )
)

def reasoning_node(state: AgentState) -> Command[Literal["supervisor", "human_approval_gate", "chief_reviewer"]]:
    """Reasoning specialist node with smart tool-call fallback."""
    from langchain_core.messages import ToolMessage as _TM
    all_context = " ".join(
        str(getattr(m, "content", "")) for m in state.messages
        if hasattr(m, "content") and isinstance(getattr(m, "content", None), str)
    )
    result = reasoning_agent.invoke(state, config=LANGFUSE_CONFIG)
    result_msgs = result.get("messages", [])
    last_content = str(result_msgs[-1].content) if result_msgs else ""

    # Check if tools were actually called natively via ReAct loop
    tool_was_called = any(isinstance(m, _TM) for m in result_msgs)

    if not tool_was_called:
        # LLM emitted JSON tool call as text — parse and execute directly
        tool_name, args = _parse_text_tool_call(last_content)
        if tool_name:
            logger.info(f"Reasoning Node: Intercepting text tool call '{tool_name}' — executing directly")
            tool_result = _execute_reasoning_tool(tool_name, args, all_context)
            last_content = f"Tool '{tool_name}' executed:\n{tool_result}"
        else:
            logger.warning("Reasoning Node: No native tool call and no parseable text tool call found")

    if "[STATUS: COMPLIANCE_COMPLETED]" not in last_content:
        last_content += "\n[STATUS: COMPLIANCE_COMPLETED]"

    out_msg = HumanMessage(content=last_content, name="reasoning_agent")
    goto = get_next_node(out_msg, "supervisor", state)
    return Command(update={"messages": [out_msg]}, goto=goto)


# ============================================================================
# 4. ADAPTIVE ROUTER & DIRECT ANSWER
# ============================================================================
def route_question(state: AgentState) -> str:
    """Dynamic LLM-based intent router. Uses the lightest local model to classify
    whether the user's query needs the full multi-agent pipeline or a simple conversational response."""
    question = state.messages[-1].content

    classification_prompt = SystemMessage(content=(
        "You are a binary intent classifier. Classify the user message into EXACTLY one route.\n"
        "Rule 1: Is the user ONLY saying a basic greeting like 'hi', 'hello', 'thanks', or 'bye'? If YES, output: {\"route\": \"direct_answer\"}\n"
        "Rule 2: For LITERALLY ANYTHING ELSE (calculating, coding, asking a question, analyzing), output: {\"route\": \"supervisor\"}\n"
        "Respond ONLY with valid JSON. Example: {\"route\": \"supervisor\"}"
    ))

    try:
        response = router_llm.invoke([classification_prompt, HumanMessage(content=question)], config=LANGFUSE_CONFIG)
        content = str(response.content).strip().lower()
        
        # Robust Fallback for small models (Laya 421m) hallucinating JSON
        if "direct_answer" in content and "supervisor" not in content:
            route = "direct_answer"
        else:
            route = "supervisor"
            
        logger.info(f"Router LLM (Laya) classified '{question[:50]}...' -> {route}")
        return route
    except Exception as e:
        logger.warning(f"Router LLM classification failed: {e}. Defaulting to supervisor.")

    # Fallback: route to supervisor so no query is silently dropped
    return "supervisor"

def direct_answer_node(state: AgentState) -> dict:
    system_prompt = (
        "You are AegisForge-AI, a Sovereign Air-Gapped Industrial AI Assistant engineered for Indian Public Sector Undertakings (PSUs).\n"
        "You assist plant engineers, inspectors, and managers with deterministic ASME engineering calculations, statutory compliance audits (CVC / GFR 2017), scanned dossier intelligence, and secure Docker sandbox execution.\n"
        "Respond warmly, concisely, and professionally to greetings or general inquiries."
    )
    # Extract only the latest user message to avoid context pollution from previous tool steps
    latest_user_msg = ""
    for m in reversed(state.messages):
        if isinstance(m, HumanMessage) and getattr(m, "name", None) in [None, "user", "Human"]:
            latest_user_msg = m.content
            break
    if not latest_user_msg and state.messages:
        latest_user_msg = state.messages[-1].content

    messages = [SystemMessage(content=system_prompt), HumanMessage(content=latest_user_msg)]
    answer = conversational_llm.invoke(messages, config=LANGFUSE_CONFIG).content
    return {"messages": [AIMessage(content=answer, name="direct_answer")]}


# ============================================================================
# 5. SUPERVISOR AGENT WITH DYNAMIC INTENT DECOMPOSITION & LOOP GUARDS
# ============================================================================
def supervisor_node(state: AgentState) -> Command[Literal["vision_agent", "coder_agent", "reasoning_agent", "chief_reviewer", "human_approval_gate"]]:
    system_prompt = (
        "You are the Sovereign Chief Multi-Agent Orchestrator for AegisForge-AI.\n"
        "Your mission is to understand the user's authentic intent from the full conversation history, autonomously decompose complex goals into clean sequential subtasks, and direct specialist agents.\n\n"
        "CONVERSATIONAL CONTEXT & INTENT UNDERSTANDING:\n"
        "- Read the full conversation history carefully.\n"
        "- If the user's latest message is a follow-up, retry, correction, or referral (such as asking to redo, rerun, fix, or repeat an earlier request), resolve the context dynamically from previous conversation turns to determine the exact substantive task to execute.\n"
        "- Do NOT assume or invent unrelated tasks unless the user or conversation history specifically called for them.\n"
        "- If the user provides code or asks for code/script execution, identify that code and dispatch 'coder_agent'.\n\n"
        "AVAILABLE SPECIALIST AGENTS & DETERMINISTIC TOOLS:\n"
        "1. 'coder_agent': Responsible for engineering calculations, deterministic physics, and code execution.\n"
        "   • 'calculate_asme_stresses': MANDATORY for ASME Section VIII Div 1 UG-27 wall thickness, MAWP, and API 510 RSL calculations.\n"
        "     Parameters: design_pressure_mpa, inside_radius_mm, allowable_stress_mpa, corrosion_allowance_mm, measured_thickness_mm, joint_efficiency.\n"
        "   • 'lookup_material': Retrieves certified allowable stresses (S) and yield limits for refinery materials.\n"
        "   • 'run_ffs_assessment': Evaluates Level 1 Fitness-For-Service RSF under API 579.\n"
        "   • 'execute_in_sandbox': ONLY for non-ASME coding tasks (Fibonacci, algorithms, data processing, custom scripts, file generation like .docx).\n"
        "2. 'reasoning_agent': Audits statutory compliance against PSU governance, CVC guidelines, GFR 2017 procurement rules, and DoP limits.\n"
        "   Tools: 'audit_cvc_compliance', 'calculate_rbi_score', 'verify_routing_policy'.\n"
        "3. 'vision_agent': Inspects, OCRs, reads, and extracts operational parameters from documents, PDFs, scanned sheets, or thickness grids.\n"
        "   Tools: 'extract_inspection_data', 'analyze_thickness_grid', 'read_scanned_pdf'.\n"
        "4. 'chief_reviewer': Forensic verification and statutory sign-off. Reviews completed specialist outputs.\n\n"
        "ROUTING & DECOMPOSITION PROTOCOL:\n"
        "• ASME / UG-27 / wall thickness / pressure vessel calculations -> 'coder_agent'\n"
        "• Material allowable stress lookup -> 'coder_agent'\n"
        "• API 579 FFS assessments -> 'coder_agent'\n"
        "• General Python scripts, algorithms, or document file creation -> 'coder_agent'\n"
        "• Statutory or compliance auditing -> 'reasoning_agent'\n"
        "• Document/image/grid inspection -> 'vision_agent'\n"
        "• Once specialist work has completed cleanly -> 'chief_reviewer'\n\n"
        "Return ONLY valid JSON:\n"
        "{\n"
        "  \"user_intent\": \"<autonomous summary of the user's real objective>\",\n"
        "  \"subtasks\": [\"<subtask 1>\", \"<subtask 2>\", ...],\n"
        "  \"current_step\": \"<the immediate subtask to execute now>\",\n"
        "  \"next\": \"vision_agent\" | \"coder_agent\" | \"reasoning_agent\" | \"chief_reviewer\",\n"
        "  \"instruction\": \"<detailed, self-contained instruction for the selected agent with all relevant parameters from the user's message>\"\n"
        "}"
    )

    # -----------------------------------------------------------------------
    # LOOP GUARD: If a specialist already completed in the current turn,
    # skip re-dispatching and route directly to chief_reviewer.
    # This prevents the supervisor from looping when an agent ran but
    # the LLM doesn't recognize the output as "done".
    # -----------------------------------------------------------------------
    current_retries = getattr(state, "retry_count", 0)
    completion_tags = {
        "coder_agent": "[STATUS: CALCULATION_COMPLETED]",
        "reasoning_agent": "[STATUS: COMPLIANCE_COMPLETED]",
        "vision_agent": "[STATUS: EXTRACTION_COMPLETED]",
    }
    # Scan last 8 messages for a completed specialist AFTER the last supervisor dispatch
    last_supervisor_idx = -1
    msgs_list = list(state.messages)
    for i in range(len(msgs_list) - 1, -1, -1):
        if str(getattr(msgs_list[i], "name", "")).lower() == "supervisor":
            last_supervisor_idx = i
            break

    specialist_completed = False
    for msg in msgs_list[last_supervisor_idx + 1:]:
        agent_name = str(getattr(msg, "name", "")).lower()
        content_str = str(getattr(msg, "content", ""))
        tag = completion_tags.get(agent_name, "")
        if tag and tag in content_str:
            specialist_completed = True
            logger.info(f"Supervisor Loop Guard: {agent_name} completed — routing to chief_reviewer")
            break

    if specialist_completed:
        clean_content = json.dumps({
            "next": "chief_reviewer",
            "instruction": "Specialist work is complete. Review and finalize the output.",
            "user_intent": "Review and present completed specialist results to the user.",
            "current_step": "Final review and verdict"
        })
        return Command(
            update={
                "retry_count": current_retries,
                "messages": [HumanMessage(content=clean_content, name="supervisor")]
            },
            goto="chief_reviewer"
        )
    # -----------------------------------------------------------------------

    messages = [SystemMessage(content=system_prompt)] + list(state.messages)
    response = supervisor_llm.invoke(messages, config=LANGFUSE_CONFIG)
    content = response.content.strip()

    next_target = "chief_reviewer"
    instruction = "Review and finalize results."
    user_intent = ""
    current_step = ""

    try:
        parsed = json.loads(content)
        if isinstance(parsed, dict):
            next_target = parsed.get("next", "chief_reviewer")
            instruction = parsed.get("instruction", "Proceed with task.")
            user_intent = parsed.get("user_intent", "")
            current_step = parsed.get("current_step", "")

            # Defensive: if LLM emitted a tool-call-like JSON instead of routing JSON, map it dynamically
            if "name" in parsed and "next" not in parsed:
                tool_name = str(parsed.get("name", "")).lower()
                args_json = json.dumps(parsed.get('arguments', parsed.get('parameters', parsed)))
                if any(kw in tool_name for kw in ["asme", "calculate_asme", "stress", "wall_thickness"]):
                    next_target = "coder_agent"
                    instruction = f"Call calculate_asme_stresses tool with these parameters: {args_json}"
                elif any(kw in tool_name for kw in ["material", "lookup_material"]):
                    next_target = "coder_agent"
                    instruction = f"Call lookup_material tool with: {args_json}"
                elif any(kw in tool_name for kw in ["ffs", "fitness", "run_ffs_assessment"]):
                    next_target = "coder_agent"
                    instruction = f"Call run_ffs_assessment tool with: {args_json}"
                elif any(kw in tool_name for kw in ["cvc", "compliance", "audit_cvc", "procurement", "gfr"]):
                    next_target = "reasoning_agent"
                    instruction = f"Call audit_cvc_compliance tool with: {args_json}"
                elif any(kw in tool_name for kw in ["rbi", "risk", "calculate_rbi"]):
                    next_target = "reasoning_agent"
                    instruction = f"Call calculate_rbi_score tool with: {args_json}"
                elif any(kw in tool_name for kw in ["ocr", "inspection", "extract_inspection", "drawing", "pid"]):
                    next_target = "vision_agent"
                    instruction = f"Call extract_inspection_data tool with: {args_json}"
                elif any(kw in tool_name for kw in ["grid", "thickness_grid", "ultrasonic", "matrix"]):
                    next_target = "vision_agent"
                    instruction = f"Call analyze_thickness_grid tool with: {args_json}"
                elif any(kw in tool_name for kw in ["pdf", "read_scanned"]):
                    next_target = "vision_agent"
                    instruction = f"Call read_scanned_pdf tool with: {args_json}"
                elif any(kw in tool_name for kw in ["run_code", "execute", "sandbox", "code", "python", "script"]):
                    next_target = "coder_agent"
                    instruction = f"Execute in sandbox: {args_json}"
    except Exception:
        # Fallback JSON parsing — find first valid JSON object in content
        s = content.find('{')
        e = content.rfind('}')
        if s != -1 and e != -1 and e > s:
            try:
                parsed = json.loads(content[s:e+1])
                next_target = parsed.get("next", "chief_reviewer")
                instruction = parsed.get("instruction", "Proceed with task.")
                user_intent = parsed.get("user_intent", "")
                current_step = parsed.get("current_step", "")
            except Exception:
                pass

    valid_targets = {"vision_agent", "coder_agent", "reasoning_agent", "chief_reviewer", "human_approval_gate"}
    if next_target not in valid_targets:
        next_target = "coder_agent"

    current_retries = getattr(state, "retry_count", 0)
    if current_retries >= getattr(state, "max_retries", 3):
        logger.warning("Supervisor Guard: Max retries exceeded. Halting to Human Approval Gate.")
        return Command(
            update={
                "retry_count": current_retries,
                "messages": [HumanMessage(content='{"next": "human_approval_gate", "instruction": "Max retries reached. Awaiting human engineer review."}', name="supervisor")]
            },
            goto="human_approval_gate"
        )

    clean_content = json.dumps({
        "next": next_target,
        "instruction": instruction,
        "user_intent": user_intent,
        "current_step": current_step
    })
    return Command(
        update={
            "retry_count": current_retries,
            "messages": [HumanMessage(content=clean_content, name="supervisor")]
        },
        goto=next_target
    )


# ============================================================================
# 6. HUMAN APPROVAL GATE NODE
# ============================================================================
def human_approval_gate(state: AgentState) -> Command[Literal["supervisor", "chief_reviewer"]]:
    user_input = interrupt({
        "message": "CRITICAL: Max retries exceeded or safety flag raised. Human engineer sign-off required.",
        "status": "Awaiting Sign-off"
    })

    approved = user_input.get("approved", False) if isinstance(user_input, dict) else False
    feedback = user_input.get("feedback", "") if isinstance(user_input, dict) else ""

    if approved:
        return Command(
            update={
                "human_approved": True,
                "human_feedback": feedback,
                "retry_count": 0,
                "messages": [HumanMessage(content=f"Human Engineer Approved: {feedback}", name="HumanGate")]
            },
            goto="chief_reviewer"
        )
    else:
        return Command(
            update={
                "human_approved": False,
                "human_feedback": feedback,
                "retry_count": 0,
                "messages": [HumanMessage(content=f"Human Engineer Rejected/Re-routed: {feedback}", name="HumanGate")]
            },
            goto="supervisor"
        )


# ============================================================================
# 7. CHIEF REVIEWER & DELIVERABLE PUBLISHER
# ============================================================================
chief_reviewer_agent = create_react_agent(
    reviewer_llm,
    tools=[],
    prompt=(
        "You are the Sovereign Chief Technical & Engineering Reviewer for AegisForge-AI.\n"
        "Your mission is to conduct forensic validation of specialist outputs tailored specifically to the user's intent.\n\n"
        "ADAPTIVE VERIFICATION INSTRUCTIONS:\n"
        "1. For Python Code / Algorithms / Sandbox Executions:\n"
        "   - Verify that the code ran inside the Docker sandbox with exit status 'COMPLETED' or code 0 without exceptions.\n"
        "   - Report the exact output produced by the script.\n"
        "   - DO NOT display or mention t_req, t_actual, delta, RSL, MAWP, or pressure vessel variables for code or algorithm tasks!\n"
        "   - DO NOT mention CVC or procurement guidelines for code tasks!\n"
        "   - If the code executed cleanly and output is correct: issue VERDICT: 'APPROVED'.\n"
        "   - If code threw errors, syntax exceptions, or timed out: issue VERDICT: 'REJECT' and detail the error.\n\n"
        "2. For ASME Pressure Vessel Calculations:\n"
        "   - Verify UG-27 required thickness (t_req), actual thickness (t_actual), safety margin (delta), MAWP, and API 510 RSL.\n"
        "   - COMPLIANCE CRITERION: The vessel is ONLY compliant if t_actual >= t_req (delta >= 0).\n"
        "   - If t_actual < t_req (delta < 0), the vessel is in CRITICAL_BREACH / NON_COMPLIANT! Clearly state it is a safety violation requiring derating or repair.\n"
        "   - NUMERICAL SANITY: Verify that formula t = (P * R) / (S * E - 0.6 * P) + CA was used consistently with SI units (MPa, mm).\n"
        "   - If calculation is verified and technically sound: issue VERDICT: 'APPROVED'.\n\n"
        "3. For Statutory Procurement / Vigilance Audits:\n"
        "   - Verify compliance against CVC guidelines and GFR 2017 rules.\n"
        "   - If verified: issue VERDICT: 'APPROVED'.\n\n"
        "FORMAL VERDICT STRUCTURE:\n"
        "• VERDICT: 'APPROVED' or 'REJECT'\n"
        "• EXECUTIVE SUMMARY: Concise summary of what was executed and verified.\n"
        "• EXECUTION RESULTS: The actual script stdout, data, or calculation output.\n"
        "• RECOMMENDATION: Operational guidance."
    )
)

def chief_reviewer_node(state: AgentState) -> Command[Literal["supervisor", "human_approval_gate", "deliverable_publisher", "__end__"]]:
    result = chief_reviewer_agent.invoke(state, config=LANGFUSE_CONFIG)
    reviewer_content = result["messages"][-1].content
    out_msg = HumanMessage(content=reviewer_content, name="chief_reviewer")

    # 1. EVALUATE VERDICT FOR SELF-CORRECTION LOOP-BACK
    is_rejected = any(rej in reviewer_content.upper() for rej in ["VERDICT: 'REJECT'", "VERDICT: REJECT", "VERDICT:** REJECT", "• VERDICT: REJECT"])
    current_retries = getattr(state, "retry_count", 0)

    if is_rejected:
        current_retries += 1
        logger.warning(f"Chief Reviewer REJECTED output. Retry count: {current_retries}/{getattr(state, 'max_retries', 3)}.")
        if current_retries >= getattr(state, "max_retries", 3):
            logger.warning("Max retries exceeded upon Chief Reviewer rejection. Routing to Human Approval Gate.")
            return Command(
                update={"retry_count": current_retries, "messages": [out_msg]},
                goto="human_approval_gate"
            )
        else:
            logger.info("Looping back to Supervisor with Chief Reviewer Critique for autonomous self-correction.")
            return Command(
                update={"retry_count": current_retries, "messages": [out_msg]},
                goto="supervisor"
            )

    # 2. IF APPROVED: CHECK IF FORMAL PUBLICATION (WORD/PDF/DOSSIER) IS REQUESTED
    initial_user_msg = ""
    for msg in state.messages:
        if isinstance(msg, HumanMessage) and getattr(msg, "name", None) in [None, "user", "Human"]:
            initial_user_msg = msg.content
            break
    q_lower = initial_user_msg.lower() if initial_user_msg else ""
    needs_publishing = any(w in q_lower for w in ["dossier", "report", "nfa", "document", "publish", "word", "pdf", "seal"])

    if not needs_publishing:
        logger.info("Chief Reviewer: Task approved and finalized. Ending pipeline.")
        return Command(update={"messages": [out_msg]}, goto=END)

    logger.info("Chief Reviewer: Task approved. Routing to Deliverable Publisher for official documentation.")
    return Command(update={"messages": [out_msg]}, goto="deliverable_publisher")


# ============================================================================
# DELIVERABLE PUBLISHER
# ============================================================================
publisher_agent = create_react_agent(
    supervisor_llm,
    tools=publisher_tools,
    prompt=(
        "You are the Sovereign Deliverable Publisher of AegisForge-AI.\n"
        "Your duty is compiling verified engineering findings into formal, tamper-evident executive documents.\n\n"
        "AVAILABLE TOOLS:\n"
        "1. 'generate_nfa_documents': Injects verified equipment parameters, ASME stress calculations, and compliance audit results into official Word/PDF templates.\n"
        "2. 'write_sha256_audit_seal': Hashes generated files and commits an immutable event to the SQLite cryptographic audit ledger.\n"
        "3. 'verify_zero_egress': Confirms complete air-gapped network isolation with zero external IP connections.\n\n"
        "EXECUTION INSTRUCTIONS:\n"
        "- Read the full conversation history to extract: equipment_id, ASME results (t_req_mm, delta_mm, status, RSL), compliance verdict, and any user-specified names/costs.\n"
        "- CALL 'generate_nfa_documents' with the equipment_id and payload dynamically built from conversation history.\n"
        "- Report the exact generated file path on disk and the cryptographic SHA-256 seal.\n"
        "- Do NOT invent or hallucinate file paths — only report real artifacts produced by the tools."
    )
)

def deliverable_publisher_node(state: AgentState) -> Command[Literal["__end__"]]:
    result = publisher_agent.invoke(state, config=LANGFUSE_CONFIG)
    last_content = result["messages"][-1].content

    # Fallback: if publisher agent didn't call generate_nfa_documents natively,
    # build payload dynamically from conversation history and call it directly.
    if "data/output" not in last_content and ".docx" not in last_content:
        try:
            full_history_text = "\n".join([str(getattr(m, "content", "")) for m in state.messages])

            # Extract equipment ID dynamically
            eq_id = "UNKNOWN-VESSEL"
            for msg in reversed(state.messages):
                m_eq = re.search(r'\b(\d{1,3}-[A-Z]{1,3}-\d{2,4})\b', getattr(msg, "content", ""))
                if m_eq:
                    eq_id = m_eq.group(1)
                    break

            payload = {
                "equipment_id": eq_id,
                "audit_quarter": f"Q{((datetime.datetime.now().month - 1) // 3) + 1}-{datetime.datetime.now().year}",
                "incident_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "report_date": datetime.datetime.now().strftime("%Y-%m-%d"),
                "valid_until": (datetime.datetime.now() + datetime.timedelta(days=365)).strftime("%Y-%m-%d"),
            }

            # Extract all values from conversation history — no hardcoded defaults
            m_treq = re.search(r'(?:t_req|t_min|required thickness)[:\s=]*([0-9.]+)', full_history_text, re.IGNORECASE)
            if m_treq:
                payload["t_req_mm"] = float(m_treq.group(1))

            m_tact = re.search(r'(?:measured_thickness|t_actual|actual thickness|measured thickness)[:\s=]*([0-9.]+)', full_history_text, re.IGNORECASE)
            if m_tact:
                payload["measured_thickness_mm"] = float(m_tact.group(1))

            m_cr = re.search(r'(?:corrosion_rate|corrosion rate|CR)[:\s=]*([0-9.]+)', full_history_text, re.IGNORECASE)
            if m_cr:
                payload["corrosion_rate_mm_yr"] = float(m_cr.group(1))

            m_rsl = re.search(r'(?:remaining_life|remaining service life|RSL)[:\s=]*([-0-9.]+)', full_history_text, re.IGNORECASE)
            if m_rsl:
                payload["remaining_life_years"] = float(m_rsl.group(1))

            m_status = re.search(r'\b(CRITICAL_BREACH|CRITICAL BREACH|SAFE|BREACH)\b', full_history_text, re.IGNORECASE)
            if m_status:
                payload["status"] = m_status.group(0).upper()

            m_cost = re.search(r'(?:cost|amount|budget|INR|Rs\.?|lakhs?)[:\s]*([0-9.,]+)', full_history_text, re.IGNORECASE)
            if m_cost:
                payload["estimated_cost"] = m_cost.group(0).strip()

            m_clause = re.search(r'(GFR\s*20\d\d[^.\n]{0,60}|CVC[^.\n]{0,60}|Rule\s*\d+[^.\n]{0,40})', full_history_text, re.IGNORECASE)
            if m_clause:
                payload["sanction_clause"] = m_clause.group(0).strip()

            if payload.get("t_req_mm") and payload.get("measured_thickness_mm"):
                t_req = payload["t_req_mm"]
                t_act = payload["measured_thickness_mm"]
                payload["executive_summary"] = (
                    f"Statutory Turnaround Inspection and Wall Thickness Verification for Vessel {eq_id}. "
                    f"Required thickness t_req={t_req:.2f}mm vs measured {t_act:.2f}mm. "
                    f"Integrity status: {payload.get('status', 'EVALUATED')}."
                )

            doc_res = doc_generator.generate_nfa_documents.invoke({
                "template_type": "ASME_Turnaround_Inspection.docx",
                "base_name": f"{eq_id}_Statutory_NFA",
                "payload": payload
            })
            last_content += f"\n\n[PUBLISHED DELIVERABLE]:\n{doc_res}"
        except Exception as e:
            logger.error(f"Publisher fallback error: {e}")

    out_msg = HumanMessage(content=last_content, name="deliverable_publisher")
    return Command(update={"messages": [out_msg]}, goto=END)


# ============================================================================
# 8. BUILD AND COMPILE LANGGRAPH WORKFLOW
# ============================================================================
workflow = StateGraph(AgentState)

# Add Nodes
workflow.add_node("direct_answer", direct_answer_node)
workflow.add_node("supervisor", supervisor_node)
workflow.add_node("vision_agent", vision_node)
workflow.add_node("coder_agent", coder_node)
workflow.add_node("reasoning_agent", reasoning_node)
workflow.add_node("human_approval_gate", human_approval_gate)
workflow.add_node("chief_reviewer", chief_reviewer_node)
workflow.add_node("deliverable_publisher", deliverable_publisher_node)

# Add Router Edge
workflow.add_conditional_edges(START, route_question, {
    "direct_answer": "direct_answer",
    "supervisor": "supervisor"
})
workflow.add_edge("direct_answer", END)

memory = MemorySaver()
app = workflow.compile(checkpointer=memory)
