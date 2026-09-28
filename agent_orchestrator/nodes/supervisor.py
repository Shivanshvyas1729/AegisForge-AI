"""
AegisForge-AI — Supervisor Node
==================================
Orchestrates the multi-agent pipeline with loop guards and retry limits.
Fix #4: uses state turn index to avoid false-triggering on old completion tags.
"""

import json
import logging
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage
from langgraph.types import Command

from agent_orchestrator.state import AgentState
from agent_orchestrator.models import supervisor_llm, LANGFUSE_CONFIG

logger = logging.getLogger("AegisForge.Supervisor")

_COMPLETION_TAGS = {
    "coder_agent":    "[STATUS: CALCULATION_COMPLETED]",
    "reasoning_agent": "[STATUS: COMPLIANCE_COMPLETED]",
    "vision_agent":   "[STATUS: EXTRACTION_COMPLETED]",
}

_VALID_TARGETS = {
    "vision_agent", "coder_agent", "reasoning_agent",
    "chief_reviewer", "human_approval_gate"
}

_SYSTEM_PROMPT = (
    "You are the Sovereign Chief Multi-Agent Orchestrator for AegisForge-AI.\n"
    "Your mission is to understand the user's authentic intent from the full conversation history, "
    "autonomously decompose complex goals into clean sequential subtasks, and direct specialist agents.\n\n"
    "CONVERSATIONAL CONTEXT & INTENT UNDERSTANDING:\n"
    "- Read the full conversation history carefully.\n"
    "- If the user's latest message is a follow-up or correction, resolve context from previous turns.\n"
    "- Do NOT assume or invent unrelated tasks.\n"
    "- If the user provides code or asks for code/script execution, dispatch 'coder_agent'.\n\n"
    "AVAILABLE SPECIALIST AGENTS & DETERMINISTIC TOOLS:\n"
    "1. 'coder_agent': ASME calculations, material lookups, API 579 FFS, code execution.\n"
    "   • 'calculate_asme_stresses': MANDATORY for ASME UG-27 wall thickness / MAWP / RSL.\n"
    "   • 'lookup_material': Certified allowable stresses for refinery materials.\n"
    "   • 'run_ffs_assessment': Fitness-For-Service RSF under API 579.\n"
    "   • 'execute_in_sandbox': ONLY for non-ASME coding tasks.\n"
    "2. 'reasoning_agent': Statutory compliance audits (CVC, GFR 2017, DoP, PAC, RBI).\n"
    "3. 'vision_agent': OCR, PDF extraction, P&ID parsing, UT grid analysis.\n"
    "4. 'chief_reviewer': Forensic verification and statutory sign-off.\n\n"
    "ROUTING PROTOCOL:\n"
    "• ASME / UG-27 / wall thickness / pressure vessel → 'coder_agent'\n"
    "• Material stress lookup → 'coder_agent'\n"
    "• API 579 FFS → 'coder_agent'\n"
    "• Python scripts / algorithms / file creation → 'coder_agent'\n"
    "• Statutory / compliance auditing → 'reasoning_agent'\n"
    "• Document / image / grid inspection → 'vision_agent'\n"
    "• Once specialist work completed cleanly → 'chief_reviewer'\n\n"
    "Return ONLY valid JSON:\n"
    "{\n"
    "  \"user_intent\": \"<autonomous summary of the user's real objective>\",\n"
    "  \"subtasks\": [\"<subtask 1>\", \"<subtask 2>\", ...],\n"
    "  \"current_step\": \"<the immediate subtask to execute now>\",\n"
    "  \"next\": \"vision_agent\" | \"coder_agent\" | \"reasoning_agent\" | \"chief_reviewer\",\n"
    "  \"instruction\": \"<detailed, self-contained instruction for the selected agent>\"\n"
    "}"
)


def supervisor_node(
    state: AgentState,
) -> Command[Literal["vision_agent", "coder_agent", "reasoning_agent",
                     "chief_reviewer", "human_approval_gate"]]:

    current_retries = state.get("retry_count", 0)

    # -----------------------------------------------------------------------
    # LOOP GUARD: check if a specialist completed AFTER the last supervisor msg
    # Fix #4: track last_supervisor_idx precisely to avoid cross-turn triggers
    # -----------------------------------------------------------------------
    msgs_list = list(state["messages"])
    last_supervisor_idx = -1
    for i in range(len(msgs_list) - 1, -1, -1):
        if str(getattr(msgs_list[i], "name", "")).lower() == "supervisor":
            last_supervisor_idx = i
            break

    specialist_completed = False
    for msg in msgs_list[last_supervisor_idx + 1:]:
        agent_name = str(getattr(msg, "name", "")).lower()
        content_str = str(getattr(msg, "content", ""))
        tag = _COMPLETION_TAGS.get(agent_name, "")
        if tag and tag in content_str:
            specialist_completed = True
            logger.info(f"Supervisor Loop Guard: {agent_name} completed — routing to chief_reviewer")
            break

    if specialist_completed:
        clean = json.dumps({
            "next": "chief_reviewer",
            "instruction": "Specialist work is complete. Review and finalize the output.",
            "user_intent": "Review and present completed specialist results to the user.",
            "current_step": "Final review and verdict"
        })
        return Command(
            update={"retry_count": 0, "messages": [HumanMessage(content=clean, name="supervisor")]},
            goto="chief_reviewer"
        )

    # -----------------------------------------------------------------------
    # MAX RETRIES GUARD
    # -----------------------------------------------------------------------
    if current_retries >= state.get("max_retries", 3):
        logger.warning("Supervisor Guard: Max retries exceeded. Halting to Human Approval Gate.")
        return Command(
            update={
                "retry_count": current_retries,
                "messages": [HumanMessage(
                    content='{"next": "human_approval_gate", "instruction": "Max retries reached."}',
                    name="supervisor"
                )]
            },
            goto="human_approval_gate"
        )

    # -----------------------------------------------------------------------
    # NORMAL DISPATCH
    # -----------------------------------------------------------------------
    messages = [SystemMessage(content=_SYSTEM_PROMPT)] + msgs_list
    response = supervisor_llm.invoke(messages, config=LANGFUSE_CONFIG)
    content = response.content.strip()

    next_target = "chief_reviewer"
    instruction = "Review and finalize results."
    user_intent = ""
    current_step = ""

    def _parse_supervisor_json(raw: str) -> dict:
        try:
            return json.loads(raw)
        except Exception:
            s = raw.find('{')
            e = raw.rfind('}')
            if s != -1 and e > s:
                try:
                    return json.loads(raw[s:e + 1])
                except Exception:
                    pass
        return {}

    parsed = _parse_supervisor_json(content)
    if parsed:
        next_target  = parsed.get("next", "chief_reviewer")
        instruction  = parsed.get("instruction", "Proceed with task.")
        user_intent  = parsed.get("user_intent", "")
        current_step = parsed.get("current_step", "")

        # Handle cases where LLM emits a tool-call JSON instead of routing JSON
        if "name" in parsed and "next" not in parsed:
            tool_name = str(parsed.get("name", "")).lower()
            args_json = json.dumps(parsed.get("arguments", parsed.get("parameters", parsed)))
            if any(kw in tool_name for kw in ["asme", "calculate_asme", "stress", "wall_thickness"]):
                next_target = "coder_agent"
                instruction = f"Call calculate_asme_stresses tool with: {args_json}"
            elif any(kw in tool_name for kw in ["material", "lookup_material"]):
                next_target = "coder_agent"
                instruction = f"Call lookup_material tool with: {args_json}"
            elif any(kw in tool_name for kw in ["ffs", "fitness"]):
                next_target = "coder_agent"
                instruction = f"Call run_ffs_assessment tool with: {args_json}"
            elif any(kw in tool_name for kw in ["cvc", "compliance", "audit_cvc", "procurement"]):
                next_target = "reasoning_agent"
                instruction = f"Call audit_cvc_compliance tool with: {args_json}"
            elif any(kw in tool_name for kw in ["rbi", "risk"]):
                next_target = "reasoning_agent"
                instruction = f"Call calculate_rbi_score tool with: {args_json}"
            elif any(kw in tool_name for kw in ["extract", "inspection", "ocr", "drawing"]):
                next_target = "vision_agent"
                instruction = f"Call extract_inspection_data tool with: {args_json}"
            elif any(kw in tool_name for kw in ["grid", "thickness_grid", "ultrasonic"]):
                next_target = "vision_agent"
                instruction = f"Call analyze_thickness_grid tool with: {args_json}"
            elif any(kw in tool_name for kw in ["pdf", "read_scanned"]):
                next_target = "vision_agent"
                instruction = f"Call read_scanned_pdf tool with: {args_json}"
            elif any(kw in tool_name for kw in ["run_code", "execute", "sandbox", "code"]):
                next_target = "coder_agent"
                instruction = f"Execute in sandbox: {args_json}"

    if next_target not in _VALID_TARGETS:
        next_target = "coder_agent"

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
