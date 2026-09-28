"""
AegisForge-AI — Agent State Definition
=======================================
Uses TypedDict (LangGraph native) instead of BaseModel for correct reducer
behaviour. Structured result fields prevent the publisher from regex-parsing
free-text conversation history (fixes hallucination risk #8 + compatibility #13).
"""

from typing import Annotated, Sequence, Optional
from typing_extensions import TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    # Core message stream — LangGraph reducer handles append logic
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Retry / human-gate controls
    retry_count: int
    max_retries: int
    human_approved: bool
    human_feedback: str

    # Task scope hint set by supervisor
    task_scope: str  # "standalone_calc" | "dossier_pipeline" | "compliance" | "auto"

    # Structured results written by specialist nodes — read by publisher directly.
    # Eliminates regex-parsing free conversation text in deliverable_publisher_node.
    last_asme_result: Optional[dict]
    last_compliance_result: Optional[dict]
    equipment_id: Optional[str]


def default_state() -> dict:
    """Returns a clean initial AgentState dict."""
    return {
        "messages": [],
        "retry_count": 0,
        "max_retries": 3,
        "human_approved": False,
        "human_feedback": "",
        "task_scope": "auto",
        "last_asme_result": None,
        "last_compliance_result": None,
        "equipment_id": None,
    }
