"""
tools/api_579_ffs_tool.py
API 579-1/ASME FFS-1 Level 1 Fitness-For-Service (FFS) Assessment.
Evaluates Local Thin Areas (LTA) to determine if a vessel can safely operate 
even if a localized spot falls below the global required thickness.
"""

import sys
import math
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.audit_trail import append_audit_event

def evaluate_lta(t_actual_global: float, t_min_lta: float, t_req: float, flaw_length_mm: float, inside_radius_mm: float) -> dict:
    """
    Tier 1 heuristic for API 579 Level 1 FFS of a Local Thin Area.
    """
    # 1. Remaining Thickness Check: LTA must be >= 2.5 mm AND >= 50% of t_req
    min_allowable_lta = max(0.5 * t_req, 2.5)
    is_safe_thickness = t_min_lta >= min_allowable_lta
    
    # 2. Flaw Length Check: Must not exceed critical longitudinal length limit
    # Approx heuristic: L <= 1.123 * sqrt(D * t_actual)
    diameter = 2.0 * inside_radius_mm
    critical_length = 1.123 * math.sqrt(diameter * t_actual_global)
    is_safe_length = flaw_length_mm <= critical_length
    
    is_acceptable = bool(is_safe_thickness and is_safe_length)
    
    if is_acceptable:
        rec = "LTA Acceptable for continued service under API 579 Level 1."
    else:
        rec = "LTA REJECTED. Requires physical repair, pressure derating, or a complex Level 2/3 FEA assessment."
        
    return {
        "is_acceptable": is_acceptable,
        "critical_flaw_length_limit_mm": round(critical_length, 2),
        "minimum_allowable_lta_thickness_mm": round(min_allowable_lta, 2),
        "thickness_check_passed": bool(is_safe_thickness),
        "length_check_passed": bool(is_safe_length),
        "recommendation": rec
    }

try:
    from langchain_core.tools import tool
    @tool
    def api_579_ffs_tool(t_actual_global: float, t_min_lta: float, t_req: float, flaw_length_mm: float, inside_radius_mm: float) -> str:
        """
        Executes an API 579 Level 1 Fitness-For-Service (FFS) evaluation on a Local Thin Area (LTA).
        
        Args:
            t_actual_global: The nominal/global measured thickness of the vessel in mm.
            t_min_lta: The minimum thickness measured exactly inside the corrosion flaw/LTA in mm.
            t_req: The ASME UG-27 required minimum thickness in mm.
            flaw_length_mm: The maximum longitudinal length of the corrosion flaw in mm.
            inside_radius_mm: The inside radius of the vessel shell in mm.
        """
        try:
            res = evaluate_lta(t_actual_global, t_min_lta, t_req, flaw_length_mm, inside_radius_mm)
            append_audit_event(
                tool_name="api_579_ffs_tool",
                inputs={"t_min_lta": t_min_lta, "flaw_length": flaw_length_mm},
                outputs=res,
                status="SUCCESS",
                caller="api_579_ffs_tool"
            )
            
            return (
                f"API 579 Level 1 LTA FFS Assessment:\n"
                f"- Assessment Verdict: {'PASS' if res['is_acceptable'] else 'FAIL'}\n"
                f"- Thickness Check: {'PASS' if res['thickness_check_passed'] else 'FAIL'} (LTA {t_min_lta} mm vs Limit {res['minimum_allowable_lta_thickness_mm']} mm)\n"
                f"- Length Check: {'PASS' if res['length_check_passed'] else 'FAIL'} (Flaw {flaw_length_mm} mm vs Limit {res['critical_flaw_length_limit_mm']} mm)\n"
                f"- Official Recommendation: {res['recommendation']}"
            )
        except Exception as e:
            return f"API 579 Assessment Error: {str(e)}"
except ImportError:
    api_579_ffs_tool = None
