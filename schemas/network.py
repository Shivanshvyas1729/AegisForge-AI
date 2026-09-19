from pydantic import BaseModel
from typing import List

class NetworkTelemetryReport(BaseModel):
    timestamp: str
    process_id: int
    is_air_gapped: bool
    external_connections: List[str]
    local_connections: List[str]
    verification_status: str
