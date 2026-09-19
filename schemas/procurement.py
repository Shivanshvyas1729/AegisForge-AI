from pydantic import BaseModel, Field
from typing import List

class ProcurementRequest(BaseModel):
    equipment_id: str = Field(..., description="The ID of the equipment")
    estimated_cost_lakhs: float = Field(..., description="Estimated cost in Lakhs (INR)")
    is_single_source: bool = Field(False, description="Is this bypassing open tendering?")
    is_emergency: bool = Field(False, description="Is this a documented industrial emergency?")
    has_pac: bool = Field(False, description="Does this have a Proprietary Article Certificate?")
    
    # Optional flags for scalable rules
    vendor_is_blacklisted: bool = Field(False, description="Is the vendor on the CVC blacklist?")

    # DYNAMIC RAG INJECTION: LLM extracts these via RAG and passes them to the tool
    applicable_cvc_clause: str = Field(..., description="The specific CVC clause extracted by the LLM")
    required_financial_authority: str = Field(..., description="The DOP authority required for this cost limit")

class AuditVerdict(BaseModel):
    is_compliant: bool
    competent_financial_authority: str
    sanction_clause: str
    violations: List[str]
