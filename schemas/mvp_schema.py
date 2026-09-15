"""
schemas/mvp_schema.py
Shared Pydantic data schemas connecting all 5 members for the Golden Path MVP.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field


class InspectionInput(BaseModel):
    """Clean parameters extracted from field inspection OCR logs."""
    equipment_id: str = Field(default="11-V-102", description="Equipment tag identifier")
    equipment_name: str = Field(default="HP Separator Drum", description="Equipment description")
    material: str = Field(default="2.25Cr-1Mo + 347 SS cladding", description="Shell base material")
    design_pressure_mpa: float = Field(default=14.5, description="Design pressure P in MPa")
    inside_radius_mm: float = Field(default=1200.0, description="Inside radius R in mm")
    allowable_stress_mpa: float = Field(default=138.0, description="Max allowable stress S in MPa")
    joint_efficiency: float = Field(default=1.0, description="Weld joint efficiency factor E")
    corrosion_allowance_mm: float = Field(default=4.0, description="Specified corrosion allowance CA in mm")
    critical_location: str = Field(default="BK-01", description="Location ID of the critical thickness point")
    measured_thickness_mm: float = Field(default=138.20, description="Actual measured wall thickness in mm")
    corrosion_rate_mm_yr: float = Field(default=0.75, description="Observed corrosion rate in mm/year")
    inspector_notes: Optional[str] = Field(default=None, description="Handwritten or marginal inspector remarks")


class CalculationOutput(BaseModel):
    """Validated ASME Section VIII Div 1 & API 510 engineering calculations."""
    t_req_mm: float = Field(..., description="Minimum required wall thickness t_min under ASME UG-27 in mm")
    measured_thickness_mm: float = Field(..., description="Actual measured thickness in mm")
    delta_mm: float = Field(..., description="Thickness margin delta (t_actual - t_req) in mm")
    is_breach: bool = Field(..., description="True if actual thickness < required minimum thickness")
    remaining_life_years: float = Field(..., description="API 510 remaining safe operating life in years")
    derated_mawp_bar: float = Field(..., description="Derated Maximum Allowable Working Pressure in barg")
    design_pressure_bar: float = Field(default=145.0, description="Original design pressure in barg")
    status: str = Field(..., description="Safety status: CRITICAL_BREACH or SAFE")
    formula_used: str = Field(
        default="t_req = (P * R) / (S * E - 0.6 * P) + CA",
        description="ASME UG-27 cylindrical shell formula"
    )


class ReasoningOutput(BaseModel):
    """DeepSeek-R1 synthesized regulatory justification and CVC compliance rationale."""
    executive_summary: str = Field(..., description="Executive problem statement")
    cvc_guideline_clause: str = Field(..., description="CVC Proprietary Article Certificate / Emergency clause")
    recommended_action: str = Field(..., description="Recommended engineering repair / replacement")
    estimated_cost: str = Field(default="Rs. 88.0 Lakhs", description="Estimated Capex/Opex expenditure")
    raw_model_response: str = Field(..., description="Full chain-of-thought text from local DeepSeek-R1")


class FinalNFAPayload(BaseModel):
    """Consolidated payload ready for Word (.docx) and PDF (.pdf) emission and Streamlit UI display."""
    inspection_data: InspectionInput
    calculation_data: CalculationOutput
    reasoning_data: ReasoningOutput
    docx_path: str = Field(..., description="Path to generated native .docx file")
    sha256_hash: str = Field(..., description="SHA-256 integrity hash of the emitted docx deliverable")
    pdf_path: Optional[str] = Field(default=None, description="Path to generated native .pdf file")
    pdf_sha256: Optional[str] = Field(default=None, description="SHA-256 integrity hash of the emitted pdf deliverable")
    generated_at: str = Field(..., description="Timestamp of document compilation")
