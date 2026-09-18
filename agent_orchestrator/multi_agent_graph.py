"""
agent_orchestrator/multi_agent_graph.py
StateGraph Assembly for Dynamic Hub-and-Spoke Architecture.
Orchestrates:
Supervisor <-> [Vision, Coder, Reasoning, General Agents]
Fallback: Supervisor -> Human Gate -> Supervisor
Final Step -> Publisher Agent.
"""

import sys
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from langgraph.graph import StateGraph, END
from agent_orchestrator.state import MultiAgentSystemState, create_initial_state
from agent_orchestrator.base_agent import OllamaOfflineException

from agent_orchestrator.supervisor_agent import supervisor_node
from agent_orchestrator.vision_agent import vision_agent_node
from agent_orchestrator.coder_agent import coder_agent_node
from agent_orchestrator.reasoning_agent import reasoning_agent_node
from agent_orchestrator.general_agent import general_agent_node
from agent_orchestrator.publisher_agent import publisher_agent_node

from tools.routing_guard import execute_human_override
from tools.audit_trail import append_audit_event
from config.settings import logger


def human_approval_gate_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    """
    Human Approval Gate Node for Human-in-the-Loop Fallbacks.
    Evaluates whether an external human operator has intervened after max retries.
    """
    logger.info("[HumanGate] Evaluating human fallback gate status...")
    override = state.get("human_override")

    if override and isinstance(override, dict) and override.get("feedback"):
        feedback = override.get("feedback")
        logger.info(f"[HumanGate] Received human feedback: {feedback}")
        state["human_feedback"] = feedback
        state["next_node"] = "supervisor"
        state["pipeline_status"] = "IN_PROGRESS"
        state["human_override"] = None # Clear the override so we don't infinitely loop
    else:
        # No override supplied; pipeline pauses waiting for operator confirmation
        state["pipeline_status"] = "GATE_WAITING_HUMAN"
        logger.warning("[HumanGate] Pipeline halted: waiting for human operator feedback.")
        entry_hash = append_audit_event(
            tool_name="human_approval_gate_node",
            inputs={"current_task": state.get("current_task", {}).get("task_name")},
            outputs={"verdict": "GATE_WAITING_HUMAN"},
            status="GATE_HOLD",
            caller="human_approval_gate_node"
        )
        state.setdefault("audit_trail_events", []).append(entry_hash)

    return state


def halt_pipeline_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    status = state.get("pipeline_status", "HALTED")
    logger.warning(f"[HaltNode] Pipeline execution halted with status: {status}")
    return state


def route_from_supervisor(state: MultiAgentSystemState) -> str:
    """Dynamic routing based on next_node set by supervisor."""
    return state.get("next_node", "halt_node")

def route_after_human_gate(state: MultiAgentSystemState) -> str:
    """Conditional edge from human gate."""
    if state.get("pipeline_status") == "GATE_WAITING_HUMAN":
        return "halt_node"
    return "supervisor"

def build_multi_agent_graph() -> StateGraph:
    builder = StateGraph(MultiAgentSystemState)

    # Register Nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("vision_agent", vision_agent_node)
    builder.add_node("coder_agent", coder_agent_node)
    builder.add_node("reasoning_agent", reasoning_agent_node)
    builder.add_node("general_agent", general_agent_node)
    builder.add_node("human_approval_gate", human_approval_gate_node)
    builder.add_node("publisher_agent", publisher_agent_node)
    builder.add_node("halt_node", halt_pipeline_node)

    # Set Entry Point
    builder.set_entry_point("supervisor")

    # Supervisor conditional routing to agents
    builder.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "vision_agent": "vision_agent",
            "coder_agent": "coder_agent",
            "reasoning_agent": "reasoning_agent",
            "general_agent": "general_agent",
            "human_approval_gate": "human_approval_gate",
            "publisher_agent": "publisher_agent",
            "halt_node": "halt_node",
        }
    )

    # Agents loop back to supervisor
    builder.add_edge("vision_agent", "supervisor")
    builder.add_edge("coder_agent", "supervisor")
    builder.add_edge("reasoning_agent", "supervisor")
    builder.add_edge("general_agent", "supervisor")

    # Human Gate conditional routing
    builder.add_conditional_edges(
        "human_approval_gate",
        route_after_human_gate,
        {
            "supervisor": "supervisor",
            "halt_node": "halt_node",
        }
    )

    builder.add_edge("publisher_agent", END)
    builder.add_edge("halt_node", END)

    return builder.compile()


def run_multi_agent_pipeline(
    user_query: str,
    uploaded_file_path: Optional[str] = None,
    human_override: Optional[Dict[str, Any]] = None,
    mock_ollama_outage: bool = False,
    mock_inspection_data: Optional[Dict[str, Any]] = None
) -> MultiAgentSystemState:
    graph = build_multi_agent_graph()
    initial_state = create_initial_state(
        user_query=user_query,
        uploaded_file_path=uploaded_file_path
    )
    if mock_inspection_data:
        initial_state["inspection_data"] = mock_inspection_data
    
    if human_override:
        # Check if the pipeline was waiting for human feedback on max retries
        initial_state["human_override"] = human_override
        # Inject existing state if we are recovering (simulated here for simplified testing)
        if "feedback" in human_override:
             initial_state["human_feedback"] = human_override["feedback"]
             initial_state["retry_count"] = 0
             # We would normally retrieve the persistent checkpoint here.
             # For now, it resumes cleanly via the initial state human_override inject.

    try:
        final_state = graph.invoke(initial_state)
        return final_state
    except OllamaOfflineException as e:
        logger.error(f"[MultiAgentPipeline] Halted due to Ollama outage: {e}")
        initial_state["pipeline_status"] = "HALTED_OLLAMA_SERVICE_UNAVAILABLE"
        return initial_state
