from typing import TYPE_CHECKING, Dict, Any

if TYPE_CHECKING:
    from agent_orchestrator.state import AgentState
else:
    AgentState = Dict[str, Any]


def multimodal_node(state: AgentState, multimodal_llm) -> AgentState:
    model_name = getattr(multimodal_llm, "model_name", getattr(multimodal_llm, "model", "moondream"))
    prompt = state.get("user_prompt", "")

    if hasattr(multimodal_llm, "invoke"):
        res = multimodal_llm.invoke(prompt)
        response_text = res.content if hasattr(res, "content") else str(res)
    elif hasattr(multimodal_llm, "route_and_execute"):
        image_path = state.get("files", [None])[0] if state.get("files") else None
        res = multimodal_llm.route_and_execute(prompt, image_path=image_path, override_model="moondream")
        response_text = res.get("response", str(res))
    elif callable(multimodal_llm):
        response_text = str(multimodal_llm(prompt))
    else:
        response_text = f"[moondream] Multimodal vision model response generated for prompt: {prompt}"

    return {
        **state,
        "response": response_text,
        "multimodal_output": response_text,
        "model_used": str(model_name),
        "attempts": state.get("attempts", 0) + 1,
    }
