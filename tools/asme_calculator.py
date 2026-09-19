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
