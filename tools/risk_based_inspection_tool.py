"""
tools/risk_based_inspection_tool.py
Simplified Level 1 Risk-Based Inspection (RBI) Engine based on API 580/581 principles.
Calculates Probability of Failure (PoF) and Consequence of Failure (CoF) to optimize inspection intervals.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.audit_trail import append_audit_event

def calculate_rbi_interval(remaining_life_years: float, design_pressure_mpa: float, fluid_toxicity: str = "Low") -> dict:
    """
    Tier 1 heuristic for RBI inspection interval.
    PoF is based on API 510 Remaining Life.
    CoF is based on Operating Pressure and Fluid Toxicity.
    """
    # 1. Determine Probability of Failure (PoF)
    if remaining_life_years < 3.0:
        pof = "High (Category 4)"
        interval_mult = 0.25  # Inspect frequently
    elif remaining_life_years < 7.0:
        pof = "Medium (Category 3)"
        interval_mult = 0.5
    else:
        pof = "Low (Category 1)"
        interval_mult = 0.8

    # 2. Determine Consequence of Failure (CoF)
    cof_score = 1
    if design_pressure_mpa > 5.0:  # High pressure
        cof_score += 1
    if fluid_toxicity.lower() in ["high", "toxic", "h2s", "sour", "acid"]:
        cof_score += 2
        
    if cof_score >= 3:
        cof = "High (Category E)"
        max_interval = 36 # Maximum 3 years between inspections
    elif cof_score == 2:
        cof = "Medium (Category C)"
        max_interval = 60 # Maximum 5 years
    else:
        cof = "Low (Category A)"
        max_interval = 120 # Maximum 10 years for safe, non-toxic, low pressure
        
    # 3. Calculate optimized interval in months
    base_interval = int(remaining_life_years * 12 * interval_mult)
    rec_interval = min(max_interval, max(6, base_interval)) # Never less than 6 months
    
    return {
        "probability_of_failure": pof,
        "consequence_of_failure": cof,
        "recommended_inspection_interval_months": rec_interval
    }

try:
    from langchain_core.tools import tool
    @tool
    def rbi_assessment_tool(remaining_life_years: float, design_pressure_mpa: float, fluid_toxicity: str = "Low") -> str:
        """
        Executes a Level 1 Risk-Based Inspection (RBI) assessment to determine PoF, CoF, 
        and the optimal next inspection interval in months.
        
        Args:
            remaining_life_years: The API 510 remaining safe life in years.
            design_pressure_mpa: The internal design pressure in MPa.
            fluid_toxicity: Hazard level of the fluid ('Low', 'Medium', 'High', 'Toxic').
        """
        try:
            res = calculate_rbi_interval(remaining_life_years, design_pressure_mpa, fluid_toxicity)
            append_audit_event(
                tool_name="rbi_assessment_tool",
                inputs={"life": remaining_life_years, "pressure": design_pressure_mpa, "toxicity": fluid_toxicity},
                outputs=res,
                status="SUCCESS",
                caller="rbi_assessment_tool"
            )
            return (
                f"API 580/581 Level 1 RBI Assessment:\n"
                f"- Probability of Failure (PoF): {res['probability_of_failure']}\n"
                f"- Consequence of Failure (CoF): {res['consequence_of_failure']}\n"
                f"- Recommended Next Inspection: {res['recommended_inspection_interval_months']} months"
            )
        except Exception as e:
            return f"RBI Assessment Error: {str(e)}"
except ImportError:
    rbi_assessment_tool = None
