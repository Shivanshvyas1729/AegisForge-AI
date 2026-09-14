from unittest.mock import MagicMock
from agent_orchestrator import build_graph, AgentState


def test_build_graph():
    mock_llm = MagicMock()
    app = build_graph(
        router_llm=mock_llm,
        coding_llm=mock_llm,
        reasoning_llm=mock_llm,
        summary_llm=mock_llm,
        multimodal_llm=mock_llm,
    )
    assert app is not None


def test_agent_state_dict():
    state: AgentState = {
        "user_prompt": "Hello world",
        "route": "coding",
        "attempts": 1,
    }
    assert state["route"] == "coding"
