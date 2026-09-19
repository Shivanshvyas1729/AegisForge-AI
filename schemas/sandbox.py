from pydantic import BaseModel
from typing import Optional

class SandboxExecutionResult(BaseModel):
    status: str
    output: str
    error_details: Optional[str] = None
