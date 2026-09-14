from agent_orchestrator.state import AgentState


def coding_node(state: AgentState, coding_llm) -> AgentState:
    model_name = getattr(coding_llm, "model_name", getattr(coding_llm, "model", "qwen2.5-coder:1.5b"))

    prompt = state.get("user_prompt", "")
    if state.get("multimodal_output"):
        prompt += f"\n[Vision Analysis Context]: {state['multimodal_output']}"

    if hasattr(coding_llm, "invoke"):
        res = coding_llm.invoke(prompt)
        response_text = res.content if hasattr(res, "content") else str(res)
    elif hasattr(coding_llm, "route_and_execute"):
        res = coding_llm.route_and_execute(prompt, override_model="qwen2.5-coder:1.5b")
        response_text = res.get("response", str(res))
    elif callable(coding_llm):
        response_text = str(coding_llm(prompt))
    else:
        response_text = f"[qwen2.5-coder:1.5b] Coding model response generated for prompt: {prompt}"

    return {
        **state,
        "response": response_text,
        "coding_output": response_text,
        "model_used": str(model_name),
        "attempts": state.get("attempts", 0) + 1,
    }
