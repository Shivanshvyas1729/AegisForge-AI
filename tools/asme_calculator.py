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


@tool
def calculate_asme_stresses(
    equipment_id: str,
    design_pressure_mpa: float,
    inside_radius_mm: float,
    allowable_stress_mpa: float,
    joint_efficiency: float,
    corrosion_allowance_mm: float,
    measured_thickness_mm: float,
    corrosion_rate_mm_yr: float
) -> dict:
    """Calculates ASME Section VIII Division 1 (UG-27) minimum thickness and MAWP."""
    print(f"\n--- EXECUTING TOOL: calculate_asme_stresses ---\n")
    logger.info(f"Executing tool: calculate_asme_stresses")
    try:
        inp = InspectionInput(
            equipment_id=equipment_id,
            design_pressure_mpa=design_pressure_mpa,
            inside_radius_mm=inside_radius_mm,
            allowable_stress_mpa=allowable_stress_mpa,
            joint_efficiency=joint_efficiency,
            corrosion_allowance_mm=corrosion_allowance_mm,
            measured_thickness_mm=measured_thickness_mm,
            corrosion_rate_mm_yr=corrosion_rate_mm_yr
        )
        calculator = AsmeCalculator()
        return calculator.evaluate_vessel_integrity(inp).model_dump()
    except Exception as e:
        logger.error(f"Error in calculate_asme_stresses: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Test for ASME Calculator
    logger.info("Testing calculate_asme_stresses...")
    result = calculate_asme_stresses.invoke({
        "equipment_id": "TEST-1",
        "design_pressure_mpa": 1.5,
        "inside_radius_mm": 1200.0,
        "allowable_stress_mpa": 137.9,
        "joint_efficiency": 1.0,
        "corrosion_allowance_mm": 3.0,
        "measured_thickness_mm": 16.5,
        "corrosion_rate_mm_yr": 0.15
    })
    logger.info(f"Result: {result}")
