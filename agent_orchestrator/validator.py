from .state import AgentState


def validator_node(state: AgentState, llm) -> AgentState:
    return {
        **state,
        "is_valid": True,
    }


def validation_decision(state: AgentState) -> str:
    if state.get("is_valid", False):
        return "end"

    if state.get("attempts", 0) >= 2:
        return "end"

    return state.get("route", "end")
