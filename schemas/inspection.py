from pydantic import BaseModel

class InspectionInput(BaseModel):
    equipment_id: str
    design_pressure_mpa: float
    inside_radius_mm: float
    allowable_stress_mpa: float
    joint_efficiency: float
    corrosion_allowance_mm: float
    measured_thickness_mm: float
    corrosion_rate_mm_yr: float

class AsmeResult(BaseModel):
    t_req_mm: float
    delta_mm: float
    is_breach: bool
    status: str
    remaining_life_years: float
    derated_mawp_mpa: float
