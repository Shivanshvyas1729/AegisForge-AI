"""
AegisForge-AI -- Pipeline Entry Point (Backward Compatibility Shim)
====================================================================
This file previously contained the entire 903-line pipeline.
It is now a thin shim that re-exports from the modular packages.

All existing imports continue to work:
    from agent_orchestrator.pipeline import app
    from agent_orchestrator.pipeline import AgentState

New modular structure:
    agent_orchestrator/
    |-- state.py           AgentState (TypedDict)
    |-- models.py          LLM instances + model name constants
    |-- tool_executor.py   JSON parser + tool dispatch helpers
    |-- nodes/
    |   |-- router.py      route_question, direct_answer_node, human_approval_gate
    |   |-- vision.py      vision_agent, vision_node
    |   |-- coder.py       coder_agent, coder_node
    |   |-- reasoning.py   reasoning_agent, reasoning_node
    |   |-- supervisor.py  supervisor_node
    |   |-- reviewer.py    chief_reviewer_agent, chief_reviewer_node
    |   `-- publisher.py   publisher_agent, deliverable_publisher_node
    `-- graph.py           workflow, app (compiled LangGraph)
"""

from agent_orchestrator.state import AgentState, default_state
from agent_orchestrator.models import (
    ROUTER_MODEL, SUPERVISOR_MODEL, CODER_MODEL,
    REASONING_MODEL, VISION_MODEL, REVIEWER_MODEL,
    CONVERSATIONAL_MODEL, REQUIRED_MODELS,
    supervisor_llm, coder_llm, reasoning_llm,
    vision_llm, reviewer_llm, conversational_llm, router_llm,
    LANGFUSE_CONFIG,
)
from agent_orchestrator.graph import app, workflow

from agent_orchestrator.nodes.router     import route_question, direct_answer_node, human_approval_gate
from agent_orchestrator.nodes.supervisor import supervisor_node
from agent_orchestrator.nodes.vision     import vision_node
from agent_orchestrator.nodes.coder      import coder_node
from agent_orchestrator.nodes.reasoning  import reasoning_node
from agent_orchestrator.nodes.reviewer   import chief_reviewer_node
from agent_orchestrator.nodes.publisher  import deliverable_publisher_node

__all__ = [
    "app", "workflow", "AgentState", "default_state",
    "ROUTER_MODEL", "SUPERVISOR_MODEL", "CODER_MODEL",
    "REASONING_MODEL", "VISION_MODEL", "REVIEWER_MODEL",
    "LANGFUSE_CONFIG",
    "route_question", "supervisor_node", "vision_node",
    "coder_node", "reasoning_node", "chief_reviewer_node",
    "deliverable_publisher_node", "human_approval_gate",
    "direct_answer_node",
]
