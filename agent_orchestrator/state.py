from typing import Literal, TypedDict
from langgraph.graph import MessagesState

class AgentState(MessagesState):
    retry_count: int
    max_retries: int
    human_approved: bool
    human_feedback: str
