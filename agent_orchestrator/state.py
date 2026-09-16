"""
agent_orchestrator/state.py
Central State Schema for the Sovereign Air-Gapped Multi-Agent Pipeline.
Enforces typed state transitions across Supervisor, Domain Workers,
Chief Technical Reviewer Gatekeeper, and Deliverable Publisher.
"""

from typing import TypedDict, List, Dict, Any, Optional


class MultiAgentSystemState(TypedDict, total=False):
    """
    Typed LangGraph state shared across all orchestrator nodes.
    Tracks execution from multimodal ingestion to cryptographic deliverable generation.
    """
    user_query: str
    uploaded_file_path: Optional[str]
    mission_plan: List[str]
    execution_mode: str  # "LOCAL_OLLAMA_AIR_GAPPED"
    inspection_data: Optional[Dict[str, Any]]
    requires_human_confirmation: bool
    human_override: Optional[Dict[str, Any]]
    calculation_data: Optional[Dict[str, Any]]
    compliance_data: Optional[Dict[str, Any]]
    review_verdict: Optional[Dict[str, Any]]
    deliverable_payload: Optional[Dict[str, Any]]
    pipeline_status: str
    audit_trail_events: List[str]


def create_initial_state(
    user_query: str,
    uploaded_file_path: Optional[str] = None
) -> MultiAgentSystemState:
    """
    Initializes a clean, standard pipeline state with default sovereign air-gapped configuration.
    """
    return {
        "user_query": user_query,
        "uploaded_file_path": uploaded_file_path,
        "mission_plan": [],
        "execution_mode": "LOCAL_OLLAMA_AIR_GAPPED",
        "inspection_data": None,
        "requires_human_confirmation": False,
        "human_override": None,
        "calculation_data": None,
        "compliance_data": None,
        "review_verdict": None,
        "deliverable_payload": None,
        "pipeline_status": "INITIALIZED",
        "audit_trail_events": [],
    }
