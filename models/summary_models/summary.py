from agent_orchestrator.state import AgentState


def summary_node(state: AgentState, summary_llm) -> AgentState:
    model_name = getattr(summary_llm, "model_name", getattr(summary_llm, "model", "llama3.2:3b"))

    prompt = state.get("user_prompt", "")
    if state.get("reasoning_output"):
        prompt += f"\n[Reasoning Analysis Context]: {state['reasoning_output']}"

    if hasattr(summary_llm, "invoke"):
        res = summary_llm.invoke(prompt)
        response_text = res.content if hasattr(res, "content") else str(res)
    elif hasattr(summary_llm, "route_and_execute"):
        res = summary_llm.route_and_execute(prompt, override_model="llama3.2:3b")
        response_text = res.get("response", str(res))
    elif callable(summary_llm):
        response_text = str(summary_llm(prompt))
    else:
        response_text = f"[llama3.2:3b] Summary model response generated for prompt: {prompt}"

    return {
        **state,
        "response": response_text,
        "summary_output": response_text,
        "model_used": str(model_name),
        "attempts": state.get("attempts", 0) + 1,
    }
