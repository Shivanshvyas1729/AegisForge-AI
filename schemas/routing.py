from pydantic import BaseModel, Field
from typing import Optional, Dict


class RoutingGuardVerdict(BaseModel):
    routing_verdict: str
    requires_human_confirmation: bool
    reason: str
    risk_level: str
    suggested_action: Optional[str] = None
