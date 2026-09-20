from pydantic import BaseModel, Field
from typing import Optional


class InspectionInput(BaseModel):
    equipment_id: str
    design_pressure_mpa: float = Field(..., gt=0)
    inside_radius_mm: float = Field(..., gt=0)
    allowable_stress_mpa: float = Field(..., gt=0)
    joint_efficiency: float = Field(..., gt=0, le=1.0)
    corrosion_allowance_mm: float = Field(..., ge=0)
    measured_thickness_mm: float = Field(..., gt=0)
    corrosion_rate_mm_yr: float = Field(..., ge=0)


class AsmeResult(BaseModel):
    t_req_mm: float
    delta_mm: float
    is_breach: bool
    status: str
    remaining_life_years: float
    derated_mawp_mpa: float


class MaterialLookupInput(BaseModel):
    material_grade: str
    temperature_c: float


class MaterialLookupResult(BaseModel):
    status: str
    error: Optional[str] = None
    material: Optional[str] = None
    temperature_c: Optional[float] = None
    allowable_stress_mpa: Optional[float] = None
    yield_strength_mpa: Optional[float] = None
    tensile_strength_mpa: Optional[float] = None


class Api579FfsInput(BaseModel):
    t_actual_global: float = Field(..., gt=0, description="Global thickness must be > 0 mm")
    t_min_lta: float = Field(..., gt=0, description="Minimum LTA thickness must be > 0 mm")
    t_req: float = Field(..., gt=0, description="Required thickness must be > 0 mm")
    flaw_length_mm: float = Field(..., gt=0, description="Flaw length must be > 0 mm")
    inside_radius_mm: float = Field(..., gt=0, description="Inside radius must be > 0 mm")
    allowable_rsf: float = Field(0.90, description="The acceptable RSF threshold (usually 0.90)")


class Api579FfsResult(BaseModel):
    status: str
    error: Optional[str] = None
    rsf: Optional[float] = None
    allowable_rsf: Optional[float] = None
    is_acceptable: Optional[bool] = None
    action: Optional[str] = None


class RbiIntervalInput(BaseModel):
    remaining_life_years: float
    design_pressure_mpa: float = Field(..., gt=0)
    fluid_toxicity: str
    toxicity_factor: int = Field(..., ge=1, le=3, description="Toxicity factor (1=Low, 2=Medium, 3=High)")
    pressure_factor: int = Field(..., ge=1, le=3, description="Pressure factor (1=Low, 2=Medium, 3=High)")
    life_factor: int = Field(..., ge=1, le=3, description="Life factor (1=Low, 2=Medium, 3=High)")


class RbiIntervalResult(BaseModel):
    status: str
    error: Optional[str] = None
    risk_category: Optional[str] = None
    recommended_interval_months: Optional[int] = None
    statutory_verdict: Optional[str] = None
