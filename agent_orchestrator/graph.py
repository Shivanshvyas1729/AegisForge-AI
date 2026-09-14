from langgraph.graph import StateGraph, START, END

from .state import AgentState
from .router import router_node, route_decision
from .validator import validator_node, validation_decision
from models import (
    coding_node,
    reasoning_node,
    summary_node,
    multimodal_node,
)


def next_after_multimodal(state: AgentState) -> str:
    if state.get("route") == "pipeline":
        return "coding"
    return "validator"


def next_after_coding(state: AgentState) -> str:
    if state.get("route") == "pipeline":
        return "reasoning"
    return "validator"


def next_after_reasoning(state: AgentState) -> str:
    if state.get("route") == "pipeline":
        return "summary"
    return "validator"


def build_graph(
    router_llm,
    coding_llm,
    reasoning_llm,
    summary_llm,
    multimodal_llm,
):

    builder = StateGraph(AgentState)

    # Router Node
    builder.add_node("router", lambda state: router_node(state, router_llm))

    # Model Nodes
    builder.add_node("coding", lambda state: coding_node(state, coding_llm))
    builder.add_node("reasoning", lambda state: reasoning_node(state, reasoning_llm))
    builder.add_node("summary", lambda state: summary_node(state, summary_llm))
    builder.add_node("multimodal", lambda state: multimodal_node(state, multimodal_llm))

    # Validator Node
    builder.add_node("validator", lambda state: validator_node(state, router_llm))

    # START → Router
    builder.add_edge(START, "router")

    # Router → Initial Model Node
    builder.add_conditional_edges(
        "router",
        route_decision,
        {
            "coding": "coding",
            "reasoning": "reasoning",
            "summary": "summary",
            "multimodal": "multimodal",
            "pipeline": "multimodal",
        }
    )

    # Model Transitions (Sequential Pipeline OR direct to Validator)
    builder.add_conditional_edges(
        "multimodal",
        next_after_multimodal,
        {
            "coding": "coding",
            "validator": "validator",
        }
    )

    builder.add_conditional_edges(
        "coding",
        next_after_coding,
        {
            "reasoning": "reasoning",
            "validator": "validator",
        }
    )

    builder.add_conditional_edges(
        "reasoning",
        next_after_reasoning,
        {
            "summary": "summary",
            "validator": "validator",
        }
    )

    builder.add_edge("summary", "validator")

    # Validator → Next Step / END
    builder.add_conditional_edges(
        "validator",
        validation_decision,
        {
            "coding": "coding",
            "reasoning": "reasoning",
            "summary": "summary",
            "multimodal": "multimodal",
            "pipeline": "multimodal",
            "end": END,
        }
    )

    return builder.compile()
