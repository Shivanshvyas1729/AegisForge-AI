from typing import Annotated, Sequence
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(BaseModel):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)
    human_approved: bool = Field(default=False)
    human_feedback: str = Field(default="")
