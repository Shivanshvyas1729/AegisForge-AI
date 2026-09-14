from .state import AgentState

VALID_ROUTES = {"coding", "reasoning", "summary", "multimodal", "pipeline"}


def router_node(state: AgentState, llm) -> AgentState:
    user_prompt = state.get("user_prompt", "")
    files = state.get("files", [])
    input_type = state.get("input_type", [])
    has_image = any("image" in it.lower() or "vision" in it.lower() for it in input_type) or bool(files)

    p_lower = user_prompt.lower()

    # Check for sequential pipeline requests
    if any(phrase in p_lower for phrase in ["pipeline", "all models", "full audit", "end to end", "complete pipeline", "run all"]):
        route = "pipeline"
    elif hasattr(llm, "classify_task"):
        route = llm.classify_task(user_prompt, has_image=has_image)
    else:
        try:
            from langchain_core.prompts import ChatPromptTemplate
            prompt_tpl = ChatPromptTemplate.from_messages([
                (
                    "system",
                    """You are a routing classifier.
Choose the best route for the user request.
Available routes:
- coding
- reasoning
- summary
- multimodal
- pipeline

Return ONLY the route name in lowercase."""
                ),
                (
                    "human",
                    """User request: {user_prompt}
Input types: {input_type}
Files: {files}"""
                ),
            ])
            chain = prompt_tpl | llm
            res = chain.invoke({
                "user_prompt": user_prompt,
                "input_type": input_type,
                "files": files
            })
            route = res.content.strip().lower() if hasattr(res, "content") else str(res).strip().lower()
        except Exception:
            route = "reasoning"

    # Map variations/aliases
    if route in ("vision", "image", "multimodel"):
        route = "multimodal"
    elif route in ("all", "composite", "full"):
        route = "pipeline"

    if route not in VALID_ROUTES:
        if any(w in p_lower for w in ["code", "python", "script", "function", "bug", "algorithm", "sort"]):
            route = "coding"
        elif any(w in p_lower for w in ["summarize", "summary", "paragraph", "tl;dr", "brief"]):
            route = "summary"
        elif any(w in p_lower for w in ["image", "drawing", "picture", "photo", "vlm", "ocr", "analyze this image"]):
            route = "multimodal"
        else:
            route = "reasoning"

    return {
        **state,
        "route": route,
        "attempts": 0
    }


def route_decision(state: AgentState) -> str:
    return state["route"]
