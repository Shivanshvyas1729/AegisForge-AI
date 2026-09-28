"""
AegisForge-AI — Router & Direct Answer Node
============================================
Fixes:
  #3  — Keyword-based fast path so greetings never hit the full pipeline,
         even when Laya is offline.
  #5  — retry_count reset to 0 on successful task completion.
"""

import logging
from typing import Literal

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Command, interrupt

from agent_orchestrator.state import AgentState
from agent_orchestrator.models import router_llm, conversational_llm, LANGFUSE_CONFIG

logger = logging.getLogger("AegisForge.Router")

# ============================================================================
# GREETING KEYWORDS — bypass Laya entirely for trivial queries  (Fix #3)
# ============================================================================
_GREETINGS = {
    "hi", "hello", "hey", "thanks", "thank you", "bye", "goodbye",
    "good morning", "good afternoon", "good evening", "good night",
    "ok", "okay", "sure", "great", "cool",
}


def route_question(state: AgentState) -> str:
    """
    Dynamic intent router.

    Fast path: keyword match for greetings → direct_answer (no LLM call).
    Slow path: Laya 421m JSON classification → supervisor or direct_answer.
    Fallback: if Laya fails → supervisor (no query is silently dropped).
    """
    question = str(state["messages"][-1].content).strip()
    q_lower = question.lower()

    # Fast path — greetings never hit the heavy pipeline (Fix #3)
    if q_lower in _GREETINGS or any(q_lower.startswith(g + " ") for g in _GREETINGS):
        logger.info(f"Router: Greeting detected via keyword → direct_answer")
        return "direct_answer"

    # LLM classification
    from langchain_core.messages import HumanMessage as _HM
    classification_prompt = SystemMessage(content=(
        "You are a binary intent classifier. Classify the user message into EXACTLY one route.\n"
        "Rule 1: Is the user ONLY saying a basic greeting like 'hi', 'hello', 'thanks', or 'bye'? "
        "If YES, output: {\"route\": \"direct_answer\"}\n"
        "Rule 2: For LITERALLY ANYTHING ELSE (calculating, coding, asking a question, analyzing), "
        "output: {\"route\": \"supervisor\"}\n"
        "Respond ONLY with valid JSON. Example: {\"route\": \"supervisor\"}"
    ))

    try:
        response = router_llm.invoke(
            [classification_prompt, _HM(content=question)],
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
    if q_clean in _GREETINGS or any(q_clean == g for g in _GREETINGS):
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
