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
    # Engineering parameters & components
    "mawp", "design pressure", "wall thickness", "corrosion allowance", "corrosion rate",
    "allowable stress", "joint efficiency", "inside radius", "outside radius",
    "pressure vessel", "separator drum", "hydrocracker", "heat exchanger",
    "piping", "flange", "nozzle", "shell", "head", "derated", "remaining life",
    "tensile", "yield strength", "hoop stress", "longitudinal stress",
    # Engineering tasks, audits & tools
    "calculate", "computation", "evaluate", "audit", "compliance", "tender",
    "procurement", "sandbox", "python script", "docker", "inspection", "thickness grid",
    "mtc", "dossier", "ocr", "extract", "simulate",
    # Units
    "mpa", "kpa", "psi", "bar", "mm/yr", "n/mm2",
}

_CLASSIFICATION_PROMPT = SystemMessage(content=(
    "You are an intent router for AegisForge-AI, an engineering and compliance platform.\n"
    "Classify the user message into EXACTLY one route: 'supervisor' or 'direct_answer'.\n\n"
    "Rules:\n"
    "- 'direct_answer': ONLY for simple casual greetings or pleasantries (e.g. 'hello', 'how are you', 'thank you', 'bye').\n"
    "- 'supervisor': For ANY engineering task, calculation, coding, technical question, or problem solving.\n\n"
    "Examples:\n"
    "User: Hello there!\n"
    "{\"route\": \"direct_answer\"}\n"
    "User: Evaluate ASME Section VIII Div 1 compliance.\n"
    "{\"route\": \"supervisor\"}\n"
    "User: Can you check the wall thickness?\n"
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
    user_input = interrupt({
        "message": "CRITICAL: Max retries exceeded or safety flag raised. "
                   "Human engineer sign-off required.",
        "status": "Awaiting Sign-off"
    })

    approved = user_input.get("approved", False) if isinstance(user_input, dict) else False
    feedback = user_input.get("feedback", "")  if isinstance(user_input, dict) else ""

    if approved:
        return Command(
            update={
                "human_approved": True,
                "human_feedback": feedback,
                "retry_count": 0,   # Fix #5 — always reset on gate exit
                "messages": [HumanMessage(
                    content=f"Human Engineer Approved: {feedback}", name="HumanGate"
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
                    content=f"Human Engineer Rejected/Re-routed: {feedback}", name="HumanGate"
                )]
            },
            goto="supervisor"
        )
