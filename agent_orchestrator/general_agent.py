"""
agent_orchestrator/general_agent.py
Llama 3.2 Node for General Review & Gatekeeping.
Executes the final Chief Reviewer logic deterministically before LLM summarization.
"""

import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.state import MultiAgentSystemState
import agent_orchestrator.base_agent as base_agent
from config.settings import MODEL_REGISTRY, logger
from tools.rag import rag_tool

def general_agent_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    logger.info("[GeneralAgent] Activated Llama-3.2.")
    current_task = state.get("current_task")
    if not current_task:
        return state
        
    model_name = MODEL_REGISTRY.get("general", "llama3.2:3b")
    instructions = current_task.get("instructions", "")
    feedback = current_task.get("feedback", "")
    
    # 1. Deterministic Chief Reviewer Gatekeeper Logic
    calc_data = state.get("calculation_data") or {}
    comp_data = state.get("compliance_data") or {}
    
    is_approved = True
    rejection_reasons = []
    
    # Evaluate Math
    asme = calc_data.get("asme_ug27", {})
    if asme.get("is_breach"):
        ffs = calc_data.get("api_579_ffs", {})
        if isinstance(ffs, dict) and not ffs.get("is_acceptable"):
            is_approved = False
            rejection_reasons.append("Critical ASME thickness breach NOT salvaged by API 579 FFS.")
            
    # Evaluate Compliance
    cvc = comp_data.get("cvc_audit", {})
    if cvc and not cvc.get("is_compliant"):
        is_approved = False
        for v in cvc.get("violations", []):
            rejection_reasons.append(f"Compliance Failure: {v}")
            
    # Evaluate Air-Gap (mocked check for MVP)
    air_gap = True
    
    state["review_verdict"] = {
        "is_approved": is_approved,
        "rejection_reasons": rejection_reasons,
        "air_gap_verified": air_gap,
        "verdict": "APPROVED_READY_FOR_PUBLISHING" if is_approved else "REJECTED_AUDIT_HOLD"
    }

    # 2. RAG Context Gathering
    rag_context = ""
    try:
        if rag_tool:
            rag_context = rag_tool.invoke("Executive summary standards and PAC approval workflow")
    except Exception as e:
        logger.warning(f"RAG failed in GeneralAgent: {e}")

    # 3. LLM Summarization Phase
    prompt = (
        f"Task: {instructions}\n"
        f"Feedback: {feedback}\n"
        f"Gatekeeper Verdict: {state['review_verdict']}\n"
        f"RAG Context: {rag_context}\n"
        "Draft a formal Chief Reviewer Executive Summary based STRICTLY on the Gatekeeper Verdict above."
    )
    try:
        output = base_agent.call_ollama(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            system_prompt="You are the Chief Technical Reviewer. Do not approve rejected reports."
        )
    except Exception as e:
        output = f"Error calling LLM: {e}"
        
    current_task["output"] = output
    state["current_task"] = current_task
    state["next_node"] = "supervisor"
    return state
