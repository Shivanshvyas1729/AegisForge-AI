from pydantic import BaseModel
from typing import Optional, Dict, Any

class DocumentGenerationRequest(BaseModel):
    base_name: str
    template_type: str
    payload: Dict[str, Any]

class DocumentGenerationResult(BaseModel):
    status: str
    docx_path: str
    document_hash: str
    audit_id: str
