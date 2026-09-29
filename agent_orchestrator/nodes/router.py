"""
AegisForge-AI — Router & Direct Answer Node
============================================
Fixes:
  #3  — Keyword-based fast path so greetings never hit the full pipeline,
         even when Laya is offline.
  #5  — retry_count reset to 0 on successful task completion.
"""

import logging
import re
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Command, interrupt

from agent_orchestrator.state import AgentState
from agent_orchestrator.models import router_llm, conversational_llm, LANGFUSE_CONFIG

logger = logging.getLogger("AegisForge.Router")

# ============================================================================
# ROUTING KEYWORDS & SAFETY GUARDS
# ============================================================================
_PURE_GREETINGS = {
    "hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye",
    "good morning", "good afternoon", "good evening", "good night",
    "namaste", "howdy",
}

_TECHNICAL_INDICATORS = {
    # Standards, Codes & Regulatory Frameworks
    "asme", "ug-27", "ug-28", "ug27", "ug28", "api", "api 579", "api-579", "ffs",
    "section viii", "div 1", "div 2", "gfr", "cvc", "rbi",
    "cmr", "cmr 2017", "dgms", "unfc", "unfc-111", "unfc-122", "unfc-333",
    # Mining & Geological parameters & components
    "borehole", "lithology", "seam", "coal", "stripping ratio", "overburden", "ob removal",
    "ash content", "moisture", "gcv", "calorific", "barakar", "raniganj", "formation",
    "geological reserve", "mineable reserve", "proved reserve", "drilling", "core log",
    "parliamentary", "parliament", "pq", "lok sabha", "rajya sabha", "ministry of coal",
    "cmpdi", "cil", "ecl", "bccl", "ccl", "wcl", "secl", "mcl", "ncl", "colliery",
    "word cloud", "topic cloud", "topic model", "dossier", "production grid",
    # Engineering parameters & components
    "mawp", "design pressure", "wall thickness", "corrosion allowance", "corrosion rate",
    "allowable stress", "joint efficiency", "inside radius", "outside radius",
    "pressure vessel", "separator drum", "hydrocracker", "heat exchanger",
    "piping", "flange", "nozzle", "shell", "head", "derated", "remaining life",
    "tensile", "yield strength", "hoop stress", "longitudinal stress",
    # Engineering tasks, audits & tools
    "calculate", "computation", "evaluate", "audit", "compliance", "tender",
    "procurement", "sandbox", "python script", "docker", "inspection", "thickness grid",
    "mtc", "ocr", "extract", "simulate",
    # Units
    "mpa", "kpa", "psi", "bar", "mm/yr", "n/mm2", "bcm", "tonnes", "mt", "kcal/kg",
}

_CLASSIFICATION_PROMPT = SystemMessage(content=(
    "You are an intent router for AegisForge-Mining, a sovereign geological, mining, and reporting workbench for CMPDI/CIL.\n"
    "Classify the user message into EXACTLY one route: 'supervisor' or 'direct_answer'.\n\n"
    "Rules:\n"
    "- 'direct_answer': ONLY for simple casual greetings or pleasantries (e.g. 'hello', 'how are you', 'thank you', 'bye').\n"
    "- 'supervisor': For ANY geological, mining, stripping ratio, reserve calculation, parliamentary inquiry, coding, or audit task.\n\n"
    "Examples:\n"
    "User: Hello there!\n"
    "{\"route\": \"direct_answer\"}\n"
    "User: Calculate stripping ratio for 50,000 BCM OB and 20,000 tonnes coal.\n"
    "{\"route\": \"supervisor\"}\n"
    "User: Answer this Parliamentary Question on coal production shortfall.\n"
    "{\"route\": \"supervisor\"}\n\n"
    "Respond ONLY with valid JSON: {\"route\": \"supervisor\"} or {\"route\": \"direct_answer\"}."
))



def route_question(state: AgentState) -> str:
    """
    Dynamic intent router with deterministic engineering guardrails and Laya 421M.

    Safety Guards (Deterministic):
    1. Engineering / technical indicators → supervisor (0ms, 100% deterministic).
    2. Numerical engineering units (MPa, mm, bar, etc.) → supervisor.
    3. Multi-sentence or long queries (> 12 words) → supervisor.

    Fast Paths (Deterministic):
    1. Pure greetings ('hi', 'namaste', etc.) → direct_answer.
    2. Short greeting phrases (<= 4 words) → direct_answer.
    3. Identity/capability questions (<= 8 words) → direct_answer.

    Model Fallback:
    - Ambiguous short queries routed via Laya 421M, defaulting to supervisor.
    """
    question = str(state["messages"][-1].content).strip()
    q_lower = question.lower()
    words = q_lower.split()

    # Safety Guard 1: Any technical / engineering / compliance indicator → supervisor
    if any(ind in q_lower for ind in _TECHNICAL_INDICATORS):
        logger.info(f"Router: Technical indicator detected → supervisor")
        return "supervisor"

    # Safety Guard 2: Any engineering units / math symbols → supervisor
    if re.search(r'\d+\s*(?:mpa|kpa|bar|psi|mm|cm|m|°c|c|yr|year|kg|kn|%)', q_lower):
        logger.info(f"Router: Engineering units / numbers detected → supervisor")
        return "supervisor"

    # Safety Guard 3: Detailed prompts (> 12 words) are never simple greetings
    if len(words) > 12:
        logger.info(f"Router: Detailed prompt ({len(words)} words) → supervisor")
        return "supervisor"

    # Fast-path 1: Pure greetings
    if q_lower in _PURE_GREETINGS:
        logger.info(f"Router: Pure greeting detected → direct_answer")
        return "direct_answer"

    # Fast-path 2: Short greeting phrases (<= 4 words)
    if len(words) <= 4 and any(q_lower.startswith(g) for g in _PURE_GREETINGS):
        logger.info(f"Router: Short greeting phrase detected → direct_answer")
        return "direct_answer"

    # Fast-path 3: Short identity/capabilities questions
    if len(words) <= 8 and any(p in q_lower for p in ["who are you", "what can you do", "help me with what", "how are you"]):
        logger.info(f"Router: Identity/capability query detected → direct_answer")
        return "direct_answer"

    # LLM classification for ambiguous short queries via Laya 421M
    from langchain_core.messages import HumanMessage as _HM
    try:
        response = router_llm.invoke(
            [_CLASSIFICATION_PROMPT, _HM(content=question)],
            config=LANGFUSE_CONFIG
        )
        content = str(response.content).strip().lower()
        if "direct_answer" in content and "supervisor" not in content:
            route = "direct_answer"
        else:
            route = "supervisor"
        logger.info(f"Router LLM classified '{question[:50]}...' → {route}")
        return route
    except Exception as e:
        logger.warning(f"Router LLM classification failed: {e}. Defaulting to supervisor.")
        return "supervisor"


def direct_answer_node(state: AgentState) -> dict:
    """Handles greetings and simple conversational queries directly."""
    system_prompt = (
        "You are AegisForge-AI, a Sovereign Air-Gapped Industrial AI Assistant engineered "
        "for Indian Public Sector Undertakings (PSUs).\n"
        "You assist plant engineers, inspectors, and managers with deterministic ASME engineering "
        "calculations, statutory compliance audits (CVC / GFR 2017), scanned dossier intelligence, "
        "and secure Docker sandbox execution.\n"
        "Respond warmly, concisely, and professionally to greetings or general inquiries."
    )
    # Extract only the latest human message to avoid context pollution
    latest_user_msg = ""
    for m in reversed(state["messages"]):
        if isinstance(m, HumanMessage) and getattr(m, "name", None) in (None, "user", "Human"):
            latest_user_msg = m.content
            break
    if not latest_user_msg and state["messages"]:
        latest_user_msg = state["messages"][-1].content

    # Fast path: instant greeting without GPU/model invocation
    q_clean = str(latest_user_msg).strip().lower()
    if q_clean in _PURE_GREETINGS or any(q_clean == g for g in _PURE_GREETINGS):
        greeting_text = (
            "Namaste! Welcome to AegisForge-AI, your Sovereign Air-Gapped Industrial AI Assistant.\n\n"
            "I assist plant engineers, inspectors, and procurement teams with:\n"
            "• **Deterministic ASME Section VIII calculations** (UG-27 shell/head thickness, MAWP, corrosion allowances)\n"
            "• **Statutory compliance audits** (CVC guidelines & GFR 2017 public procurement rules)\n"
            "• **Scanned plant dossiers & MTC inspection**\n"
            "• **Air-gapped Python code execution in Docker sandboxes**\n\n"
            "How can I help with your plant or engineering operation today?"
        )
        return {"messages": [AIMessage(content=greeting_text, name="direct_answer")]}

    try:
        answer = conversational_llm.invoke(
            [SystemMessage(content=system_prompt), HumanMessage(content=latest_user_msg)],
            config=LANGFUSE_CONFIG
        ).content
    except Exception as e:
        logger.error(f"Conversational LLM failed: {e}")
        answer = (
            f"Namaste! I am AegisForge-AI. How can I assist you with ASME calculations, "
            f"statutory compliance, or plant dossier analysis today?"
        )

    return {"messages": [AIMessage(content=answer, name="direct_answer")]}


def human_approval_gate(
    state: AgentState,
) -> Command[Literal["supervisor", "chief_reviewer"]]:
    """
    Human-in-the-loop gate. Triggered when max retries exceeded or safety
    flag raised. Resets retry_count to 0 on both approve and reject (Fix #5).
    """
    retries = state.get("retry_count", 0)
    max_r = state.get("max_retries", 3)
    asme = state.get("last_asme_result") or {}
    equipment_id = state.get("equipment_id") or asme.get("equipment_id") or "Industrial Asset"

    if retries >= max_r:
        reason = f"Execution threshold reached ({retries}/{max_r} retries). Manual engineering review required to prevent divergence."
    elif asme.get("is_breach"):
        delta = asme.get("delta_mm", 0.0)
        mawp = asme.get("derated_mawp_mpa", 0.0)
        t_req = asme.get("t_req_mm", 0.0)
        t_act = asme.get("measured_thickness_mm", 0.0)
        reason = (
            f"Mandatory Safety Interlock: Wall thickness deficit detected for {equipment_id}. "
            f"Measured thickness ({t_act:.2f} mm) is below required thickness ({t_req:.2f} mm) "
            f"by {abs(delta):.2f} mm. Derated MAWP is {mawp:.2f} MPa. Operational sign-off required."
        )
    else:
        reason = f"Operational sign-off required for {equipment_id} prior to final review."

    logger.warning(f"Human Approval Gate Triggered for {equipment_id}: {reason}")

    user_input = interrupt({
        "message": reason,
        "status": "Awaiting Sign-off",
        "equipment_id": equipment_id,
        "retry_count": retries,
        "asme_result": asme
    })

    approved = False
    feedback = ""
    if isinstance(user_input, dict):
        approved = bool(user_input.get("approved", False))
        feedback = str(user_input.get("feedback", ""))
    elif isinstance(user_input, bool):
        approved = user_input
    elif isinstance(user_input, str):
        approved = user_input.strip().lower() in ["approved", "approve", "yes", "true", "1"]
        feedback = user_input

    logger.info(f"Human Approval Gate resolved: approved={approved}, feedback='{feedback}'")

    if approved:
        return Command(
            update={
                "human_approved": True,
                "human_feedback": feedback,
                "retry_count": 0,   # Fix #5 — always reset on gate exit
                "messages": [HumanMessage(
                    content=f"Human Engineer Sign-Off: APPROVED. Engineering Directives: {feedback or 'Verified and authorized by Competent Authority.'}",
                    name="HumanGate"
                )]
            },
            goto="chief_reviewer"
        )
    else:
        return Command(
            update={
                "human_approved": False,
                "human_feedback": feedback,
                "retry_count": 0,   # Fix #5
                "messages": [HumanMessage(
                    content=f"Human Engineer Sign-Off: REJECTED / RE-ROUTED. Directives: {feedback or 'Re-evaluate parameters and re-audit.'}",
                    name="HumanGate"
                )]
            },
            goto="supervisor"
        )
