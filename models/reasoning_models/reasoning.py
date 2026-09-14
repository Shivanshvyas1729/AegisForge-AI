from agent_orchestrator.state import AgentState


def reasoning_node(state: AgentState, reasoning_llm) -> AgentState:
    model_name = getattr(reasoning_llm, "model_name", getattr(reasoning_llm, "model", "deepseek-r1:1.5b"))

    prompt = state.get("user_prompt", "")
    if state.get("coding_output"):
        prompt += f"\n[Coding Output Context]: {state['coding_output']}"

    if hasattr(reasoning_llm, "invoke"):
        res = reasoning_llm.invoke(prompt)
        response_text = res.content if hasattr(res, "content") else str(res)
    elif hasattr(reasoning_llm, "route_and_execute"):
        res = reasoning_llm.route_and_execute(prompt, override_model="deepseek-r1:1.5b")
        response_text = res.get("response", str(res))
    elif callable(reasoning_llm):
        response_text = str(reasoning_llm(prompt))
    else:
        response_text = f"[deepseek-r1:1.5b] Reasoning model response generated for prompt: {prompt}"

    return {
        **state,
        "response": response_text,
        "reasoning_output": response_text,
        "model_used": str(model_name),
        "attempts": state.get("attempts", 0) + 1,
    }
