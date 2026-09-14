from typing import TypedDict, List, Dict, Any


class AgentState(TypedDict, total=False):
    route: str
    user_prompt: str
    input_type: List[str]
    files: List[str]
    response: str
    model_used: str
    is_valid: bool
    attempts: int
    # Sequential Pipeline fields
    multimodal_output: str
    coding_output: str
    reasoning_output: str
    summary_output: str
    pipeline_steps: List[Dict[str, Any]]
