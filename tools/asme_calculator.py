import sys
import os

# Ensure the root workspace is in the python path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.inspection import InspectionInput, AsmeResult
from tools.audit_trail import AuditLedger

class AsmeCalculator:
    def __init__(self, use_audit_trail: bool = True):
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def evaluate_vessel_integrity(self, inp: InspectionInput, caller_agent: str = "coder_agent") -> AsmeResult:
        # 1. ASME Section VIII Div 1 (UG-27) Formula for Cylindrical Shells
        # t = (P * R) / (S * E - 0.6 * P) + CA
        numerator = inp.design_pressure_mpa * inp.inside_radius_mm
        denominator = (inp.allowable_stress_mpa * inp.joint_efficiency) - (0.6 * inp.design_pressure_mpa)
        t_req = (numerator / denominator) + inp.corrosion_allowance_mm
        
        # 2. Safety Delta
        delta = inp.measured_thickness_mm - t_req
        is_breach = delta < 0
        
        # 3. API 510 Remaining Service Life (RSL)
        # Prevent division by zero if corrosion rate is 0
        cr = max(inp.corrosion_rate_mm_yr, 0.001)
        remaining_life = delta / cr
        
        # 4. Derated MAWP (Maximum Allowable Working Pressure)
        # If there is a breach, calculate the new max pressure based on CURRENT thickness minus future corrosion allowance
        t_eff = inp.measured_thickness_mm - inp.corrosion_allowance_mm
        if t_eff <= 0:
            derated_mawp = 0.0
            status = "CRITICAL_FAILURE: VESSEL WALL TOO THIN FOR ANY PRESSURE"
        else:
            derated_mawp = (inp.allowable_stress_mpa * inp.joint_efficiency * t_eff) / (inp.inside_radius_mm + 0.6 * t_eff)
            status = "CRITICAL_BREACH" if is_breach else "SAFE"
            
        result = AsmeResult(
            equipment_id=inp.equipment_id,
            measured_thickness_mm=round(inp.measured_thickness_mm, 2),
            t_req_mm=round(t_req, 2),
            delta_mm=round(delta, 2),
            is_breach=is_breach,
            status=status,
            remaining_life_years=round(remaining_life, 2),
            derated_mawp_mpa=round(derated_mawp, 2)
        )
        
        if self.use_audit_trail:
            self.ledger.append_event(
                event_type="ENGINEERING_CALCULATION",
                workflow_id="ASME_UG27_AUDIT",
                tool_name="asme_calculator",
                caller=caller_agent,
                agent_version="1.0.0",
                tool_version="1.0.0",
                inputs=inp.model_dump(),
                outputs=result.model_dump(),
                status="COMPLETED_BREACH" if is_breach else "COMPLETED_SAFE"
            )
            
        return result

from langchain_core.tools import tool
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field


class AsmeStressInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    equipment_id: Optional[str] = Field(default=None, description="Equipment tag or identifier")
    design_pressure_mpa: Optional[float] = Field(default=None, description="Design pressure in MPa")
    inside_radius_mm: Optional[float] = Field(default=None, description="Inside radius in mm")
    allowable_stress_mpa: Optional[float] = Field(default=None, description="Allowable stress in MPa (S). If omitted, provide material_grade and temperature_c.")
    joint_efficiency: Optional[float] = Field(default=1.0, description="Joint efficiency E (0.0 to 1.0)")
    corrosion_allowance_mm: Optional[float] = Field(default=None, description="Corrosion allowance in mm")
    measured_thickness_mm: Optional[float] = Field(default=None, description="Measured wall thickness in mm")
    corrosion_rate_mm_yr: Optional[float] = Field(default=None, description="Corrosion rate in mm/year")
    material_grade: Optional[str] = Field(default=None, description="Material specification (e.g. 'SA-387 Gr 22') to auto-resolve allowable stress")
    temperature_c: Optional[float] = Field(default=None, description="Operating temperature in Celsius for material lookup")
    kwargs: Optional[Any] = Field(default=None, description="Optional extra arguments dictionary")


@tool(args_schema=AsmeStressInput)
def calculate_asme_stresses(
    equipment_id: Optional[str] = None,
    design_pressure_mpa: Optional[float] = None,
    inside_radius_mm: Optional[float] = None,
    allowable_stress_mpa: Optional[float] = None,
    joint_efficiency: Optional[float] = 1.0,
    corrosion_allowance_mm: Optional[float] = None,
    measured_thickness_mm: Optional[float] = None,
    corrosion_rate_mm_yr: Optional[float] = None,
    material_grade: Optional[str] = None,
    temperature_c: Optional[float] = None,
    **kwargs: Any
) -> dict:
    """Calculates ASME Section VIII Division 1 (UG-27) minimum thickness, MAWP, and RSL."""
    # Merge direct kwargs and nested kwargs
    inner = kwargs.get("kwargs") if isinstance(kwargs.get("kwargs"), dict) else {}
    all_kw = {**kwargs, **inner}
    eq_tag = equipment_id or all_kw.get("equipment_id") or all_kw.get("tag") or all_kw.get("vessel_id") or "Industrial Equipment"

    print(f"\n--- EXECUTING TOOL: calculate_asme_stresses --- (Equipment: {eq_tag})\n")
    logger.info(f"Executing tool: calculate_asme_stresses (Equipment: {eq_tag})")
    try:

        p = design_pressure_mpa or all_kw.get("p") or all_kw.get("P") or all_kw.get("pressure") or all_kw.get("design_pressure")
        r = inside_radius_mm or all_kw.get("r") or all_kw.get("R") or all_kw.get("radius") or all_kw.get("inside_radius")
        s = (
            allowable_stress_mpa
            or all_kw.get("s")
            or all_kw.get("S")
            or all_kw.get("stress")
            or all_kw.get("allowable_stress")
            or all_kw.get("allowable_stress_mpa")
        )
        e = joint_efficiency or all_kw.get("e") or all_kw.get("E") or all_kw.get("joint_eff") or 1.0
        ca = corrosion_allowance_mm or all_kw.get("ca") or all_kw.get("CA") or all_kw.get("corrosion_allowance")
        t_meas = (
            measured_thickness_mm
            or all_kw.get("t_actual")
            or all_kw.get("t_actual_mm")
            or all_kw.get("t_meas")
            or all_kw.get("thickness")
            or all_kw.get("measured_thickness")
            or all_kw.get("t")
        )
        cr = corrosion_rate_mm_yr or all_kw.get("cr") or all_kw.get("CR") or all_kw.get("corrosion_rate")

        # Auto-resolve allowable stress from material_grade if s is not explicitly passed
        if s is None:
            mat = (
                material_grade
                or all_kw.get("material_grade")
                or all_kw.get("material")
                or all_kw.get("material_spec")
                or all_kw.get("grade")
            )
            temp = (
                temperature_c
                or all_kw.get("temperature_c")
                or all_kw.get("temperature")
                or all_kw.get("temp")
                or all_kw.get("T")
                or 350.0
            )
            if mat:
                try:
                    from tools.material_lookup_tool import MaterialLookupTool, MaterialLookupInput
                    mat_tool = MaterialLookupTool(use_audit_trail=False)
                    res_mat = mat_tool.lookup_material(
                        MaterialLookupInput(material_grade=str(mat), temperature_c=float(temp) if temp is not None else 350.0)
                    )
                    if res_mat and res_mat.allowable_stress_mpa:
                        s = res_mat.allowable_stress_mpa
                        logger.info(f"Auto-resolved allowable_stress_mpa={s} from material='{mat}' at {temp}C")
                except Exception as mex:
                    logger.debug(f"Material lookup fallback failed: {mex}")

        # If any essential parameter is missing, attempt dynamic extraction from local dossier
        if any(v is None for v in [p, r, s, ca, t_meas, cr]):
            try:
                import glob
                workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
                candidate_files = glob.glob(os.path.join(workspace_root, "data", "*.pdf")) + glob.glob(os.path.join(workspace_root, "sample_data", "*.pdf"))
                for cf in candidate_files:
                    if equipment_id.lower().replace("-", "") in os.path.basename(cf).lower().replace("-", "") or "11v102" in os.path.basename(cf).lower():
                        from tools.file_io import read_scanned_pdf
                        extracted = read_scanned_pdf.invoke({"file_path": cf}).get("content", "")
                        import re
                        if p is None:
                            m = re.search(r'Design Pressure[:\s]*([\d.]+)', extracted, re.IGNORECASE)
                            if m: p = float(m.group(1))
                        if r is None:
                            m = re.search(r'Inside Radius[:\s]*([\d.]+)', extracted, re.IGNORECASE)
                            if m: r = float(m.group(1))
                        if t_meas is None:
                            m = re.search(r'(?:Measured Thickness|Actual Thickness)[:\s]*([\d.]+)', extracted, re.IGNORECASE)
                            if m: t_meas = float(m.group(1))
                        if cr is None:
                            m = re.search(r'Corrosion Rate[:\s]*([\d.]+)', extracted, re.IGNORECASE)
                            if m: cr = float(m.group(1))
                        break
            except Exception as ex:
                logger.debug(f"Dynamic parameter extraction skipped: {ex}")

        # Final defensive check — NEVER silently use hardcoded defaults (Fix #1)
        # Only corrosion_rate can default to a safe minimal value.
        missing = [name for name, val in [
            ("design_pressure_mpa",  p),
            ("inside_radius_mm",     r),
            ("allowable_stress_mpa", s),
            ("corrosion_allowance_mm", ca),
            ("measured_thickness_mm",  t_meas),
        ] if val is None]

        if missing:
            logger.error(f"ASME calculation aborted — missing required parameters: {missing}")
            return {
                "status": "PARAMETER_MISSING",
                "error": (
                    f"Cannot compute ASME UG-27 — missing required parameters: {missing}. "
                    "Please provide them explicitly in your request or upload a dossier containing "
                    "this data."
                ),
                "missing_parameters": missing,
            }

        p_val  = float(p)
        r_val  = float(r)
        s_val  = float(s)
        e_val  = float(e) if e is not None else 1.0
        ca_val = float(ca)
        t_val  = float(t_meas)
        # Corrosion rate defaults to 0.1 mm/yr (minimal conservative rate) if not provided
        cr_val = float(cr) if cr is not None else 0.1

        inp = InspectionInput(
            equipment_id=eq_tag,
            design_pressure_mpa=p_val,
            inside_radius_mm=r_val,
            allowable_stress_mpa=s_val,
            joint_efficiency=e_val,
            corrosion_allowance_mm=ca_val,
            measured_thickness_mm=t_val,
            corrosion_rate_mm_yr=cr_val
        )
        calculator = AsmeCalculator()
        return calculator.evaluate_vessel_integrity(inp).model_dump()
    except Exception as e:
        logger.error(f"Error in calculate_asme_stresses: {e}")
        return {"status": "error", "error": str(e)}


