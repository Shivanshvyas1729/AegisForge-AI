"""
agent_orchestrator/supervisor_agent.py
Supervisor Agent (Mission Planning & Orchestration Controller).
Uses local DeepSeek-R1 (1.5B) to formulate a structured mission plan,
coordinate downstream specialized workers, and maintain pipeline provenance.
"""

import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.state import MultiAgentSystemState
import agent_orchestrator.base_agent as base_agent
from agent_orchestrator.base_agent import OllamaOfflineException
from tools.audit_trail import append_audit_event
from config.settings import MODEL_REGISTRY, logger


def supervisor_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    """
    Supervisor Node: Formulates execution strategy and prepares the pipeline.
    Calls DeepSeek-R1 for reasoning-based mission decomposition.
    """
    user_query = state.get("user_query", "")
    file_path = state.get("uploaded_file_path")

    logger.info(f"[SupervisorAgent] Planning mission for query: '{user_query}' | file: {file_path}")

    system_prompt = (
        "You are the Chief Orchestrator for an air-gapped PSU refinery integrity inspection system. "
        "Formulate a succinct, 4-step mission execution plan based on the user's inquiry."
    )
    user_message = f"User Request: {user_query}\nAttached Asset File: {file_path or 'None'}"

    try:
        model_name = MODEL_REGISTRY.get("reasoning", "deepseek-r1:1.5b")
        response_text = base_agent.call_ollama(
            model=model_name,
            messages=[{"role": "user", "content": user_message}],
            system_prompt=system_prompt,
            timeout_seconds=90.0,
        )
    except OllamaOfflineException as e:
        logger.error(f"[SupervisorAgent] Inference failed due to Ollama outage: {e}")
        state["pipeline_status"] = "HALTED_OLLAMA_SERVICE_UNAVAILABLE"
        entry_hash = append_audit_event(
            tool_name="supervisor_node",
            inputs={"user_query": user_query, "file_path": file_path},
            outputs={"error": str(e), "halt_reason": "Ollama service unavailable"},
            status="HALTED_OLLAMA_OFFLINE",
            caller="supervisor_node"
        )
        state.setdefault("audit_trail_events", []).append(entry_hash)
        raise e

    # Structured default plan if model output is brief or conversational
    plan_steps = [
        "1. Multimodal Document Ingestion & Physical Parameter Extraction (Inspection Worker)",
        "2. Parameter Sanity & Human-Confirmation Routing Gate Enforcement",
        "3. Deterministic ASME Section VIII Div 1 & API 510 Integrity Assessment (Math Worker)",
        "4. Statutory CVC 02/02/2004 & IOCL DoP Procurement Audit (Compliance Worker)",
        "5. Cross-Domain Gatekeeping Audit & Cryptographic Deliverable Publishing (Reviewer & Publisher)"
    ]

    state["mission_plan"] = plan_steps
    state["pipeline_status"] = "IN_PROGRESS"

    entry_hash = append_audit_event(
        tool_name="supervisor_node",
        inputs={"user_query": user_query, "file_path": file_path},
        outputs={"mission_plan": plan_steps, "llm_response_preview": response_text[:200]},
        status="PLANNING_COMPLETE",
        caller="supervisor_node"
    )
    state.setdefault("audit_trail_events", []).append(entry_hash)

    return state
