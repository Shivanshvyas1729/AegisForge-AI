from agent_orchestrator.router import route_decision


def test_route_decision():
    state = {"route": "coding"}
    assert route_decision(state) == "coding"
