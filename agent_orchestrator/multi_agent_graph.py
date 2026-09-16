"""
agent_orchestrator/multi_agent_graph.py
StateGraph Assembly for Sovereign Air-Gapped Multi-Agent Pipeline.
Orchestrates:
Supervisor -> Inspection Worker -> [Routing Guard / Human Gate] -> Math Worker ->
Compliance Worker -> Chief Reviewer Gatekeeper -> Deliverable Publisher.
Enforces:
1. Deterministic tool passthrough.
2. 3-Way Human Approval Gate with recovery edge to Math Worker.
3. Strict causal dependency: Math Worker runs before Compliance Worker.
4. Fail-fast error handling: Ollama outages halt with HALTED_OLLAMA_SERVICE_UNAVAILABLE.
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
from agent_orchestrator.workers.inspection_worker import inspection_worker_node
from agent_orchestrator.workers.math_worker import math_worker_node
from agent_orchestrator.workers.compliance_worker import compliance_worker_node
from agent_orchestrator.reviewer_agent import reviewer_agent_node
from agent_orchestrator.publisher_agent import publisher_agent_node
from tools.routing_guard import execute_human_override
from tools.audit_trail import append_audit_event
from config.settings import logger


def human_approval_gate_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    """
    Human Approval Gate Node.
    Evaluates whether an external human operator has intervened with
    CONFIRM_UNEDITED, CORRECT_AND_RERUN, or REJECT_AND_HALT.
    If no override is present, pauses the pipeline and sets GATE_WAITING_HUMAN.
    """
    logger.info("[HumanGate] Evaluating human approval gate status...")
    override = state.get("human_override")

    if override and isinstance(override, dict):
        action = override.get("action")
        override_by = override.get("override_by", "Engineer")
        reason = override.get("reason", "Operator Override")
        corrected = override.get("corrected_parameters")

        # If override has not already been ledger-anchored, anchor it now
        if not override.get("ledger_entry_hash"):
            state = execute_human_override(
                state=state,
                action=action,
                override_by=override_by,
                override_reason=reason,
                corrected_parameters=corrected
            )
        logger.info(f"[HumanGate] Executed human override action: {action}")
    else:
        # No override supplied; pipeline pauses waiting for operator confirmation
        state["pipeline_status"] = "GATE_WAITING_HUMAN"
        logger.warning("[HumanGate] Pipeline halted: waiting for human operator confirmation.")
        entry_hash = append_audit_event(
            tool_name="human_approval_gate_node",
            inputs={"inspection_status": state.get("inspection_data", {}).get("status")},
            outputs={"verdict": "GATE_WAITING_HUMAN", "requires_human_confirmation": True},
            status="GATE_HOLD",
            caller="human_approval_gate_node"
        )
        state.setdefault("audit_trail_events", []).append(entry_hash)

    return state


def halt_pipeline_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    """
    Terminal Halt Node: Records terminal halt and ensures no deliverables are emitted.
    """
    status = state.get("pipeline_status", "HALTED")
    logger.warning(f"[HaltNode] Pipeline execution halted with status: {status}")
    entry_hash = append_audit_event(
        tool_name="halt_pipeline_node",
        inputs={"pipeline_status": status},
        outputs={"deliverable_produced": False, "final_status": status},
        status="PIPELINE_HALTED",
        caller="halt_pipeline_node"
    )
    state.setdefault("audit_trail_events", []).append(entry_hash)
    return state


def route_after_inspection(state: MultiAgentSystemState) -> str:
    """Conditional Edge: Routes clean data to math_worker, anomalous data to human gate."""
    if state.get("requires_human_confirmation", False):
        return "human_approval_gate"
    return "math_worker"


def route_after_human_gate(state: MultiAgentSystemState) -> str:
    """
    Conditional Edge:
    If operator confirmed or corrected parameters, routes to math_worker.
    If operator rejected or ticket remains unverified, routes to halt_node.
    """
    if not state.get("requires_human_confirmation", False) and state.get("pipeline_status") != "HALTED_BY_HUMAN_OVERRIDE":
        return "math_worker"
    return "halt_node"


def route_after_reviewer(state: MultiAgentSystemState) -> str:
    """Conditional Edge: Routes approved packages to publisher, rejected packages to halt_node."""
    review = state.get("review_verdict", {})
    if review.get("is_approved", False):
        return "publisher_agent"
    return "halt_node"


def build_multi_agent_graph() -> StateGraph:
    """
    Constructs and compiles the complete multi-agent LangGraph workflow.
    """
    builder = StateGraph(MultiAgentSystemState)

    # Register Nodes
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("inspection_worker", inspection_worker_node)
    builder.add_node("human_approval_gate", human_approval_gate_node)
    builder.add_node("math_worker", math_worker_node)
    builder.add_node("compliance_worker", compliance_worker_node)
    builder.add_node("reviewer_agent", reviewer_agent_node)
    builder.add_node("publisher_agent", publisher_agent_node)
    builder.add_node("halt_node", halt_pipeline_node)

    # Set Entry Point
    builder.set_entry_point("supervisor")

    # Define Transitions
    builder.add_edge("supervisor", "inspection_worker")

    # Routing Guard after inspection
    builder.add_conditional_edges(
        "inspection_worker",
        route_after_inspection,
        {
            "human_approval_gate": "human_approval_gate",
            "math_worker": "math_worker",
        }
    )

    # Human Gate: routes back into math_worker on confirm/correct, or halt_node on reject
    builder.add_conditional_edges(
        "human_approval_gate",
        route_after_human_gate,
        {
            "math_worker": "math_worker",
            "halt_node": "halt_node",
        }
    )

    # Strict Causal Ordering: Math Worker MUST run before Compliance Worker
    builder.add_edge("math_worker", "compliance_worker")

    # Compliance Worker to Chief Reviewer Gatekeeper
    builder.add_edge("compliance_worker", "reviewer_agent")

    # Chief Reviewer Gatekeeper to Publisher or Halt
    builder.add_conditional_edges(
        "reviewer_agent",
        route_after_reviewer,
        {
            "publisher_agent": "publisher_agent",
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
    mock_ollama_outage: bool = False
) -> MultiAgentSystemState:
    """
    Executes the compiled multi-agent graph with fail-fast outage handling.
    """
    graph = build_multi_agent_graph()
    initial_state = create_initial_state(
        user_query=user_query,
        uploaded_file_path=uploaded_file_path
    )
    if human_override:
        initial_state["human_override"] = human_override

    try:
        final_state = graph.invoke(initial_state)
        return final_state
    except OllamaOfflineException as e:
        logger.error(f"[MultiAgentPipeline] Halted due to Ollama outage: {e}")
        initial_state["pipeline_status"] = "HALTED_OLLAMA_SERVICE_UNAVAILABLE"
        append_audit_event(
            tool_name="multi_agent_orchestrator",
            inputs={"user_query": user_query},
            outputs={"error": str(e), "pipeline_status": "HALTED_OLLAMA_SERVICE_UNAVAILABLE"},
            status="HALTED_OLLAMA_OFFLINE",
            caller="run_multi_agent_pipeline"
        )
        return initial_state
