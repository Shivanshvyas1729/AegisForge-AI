"""
tools/risk_based_inspection_tool.py
API 581 Risk-Based Inspection (RBI) Interval Determination Tool
"""

import math


def calculate_rbi_interval(
    remaining_life_years: float,
    design_pressure_mpa: float,
    fluid_toxicity: str
) -> dict:
    """
    API 581 Risk-Based Inspection (RBI) Interval Engine.

    Combines remaining service life with process fluid toxicity and operating pressure
    to dynamically determine statutory turnaround/inspection intervals.

    Parameters
    ----------
    remaining_life_years : float
        Estimated remaining service life in years.
    design_pressure_mpa : float
        Design/operating pressure in MPa.
    fluid_toxicity : str
        Fluid toxicity category: 'Low', 'Medium', or 'High'.

    Returns
    -------
    dict
        {
            "risk_category": str,
            "recommended_interval_months": int,
            "statutory_verdict": str
        }
    """

    # 1. Type validation
    if isinstance(remaining_life_years, bool):
        return {
            "status": "ERROR",
            "error": "remaining_life_years must be a numeric value, not boolean."
        }

    if not isinstance(remaining_life_years, (int, float)):
        return {
            "status": "ERROR",
            "error": "remaining_life_years must be a numeric value."
        }

    if isinstance(design_pressure_mpa, bool):
        return {
            "status": "ERROR",
            "error": "design_pressure_mpa must be a numeric value, not boolean."
        }

    if not isinstance(design_pressure_mpa, (int, float)):
        return {
            "status": "ERROR",
            "error": "design_pressure_mpa must be a numeric value."
        }

    if not isinstance(fluid_toxicity, str):
        return {
            "status": "ERROR",
            "error": "fluid_toxicity must be a string."
        }

    # 2. NaN / Infinity validation
    if not math.isfinite(remaining_life_years):
        return {
            "status": "ERROR",
            "error": "remaining_life_years cannot be NaN or infinity."
        }

    if not math.isfinite(design_pressure_mpa):
        return {
            "status": "ERROR",
            "error": "design_pressure_mpa cannot be NaN or infinity."
        }

    # 3. Physical boundaries
    if design_pressure_mpa <= 0:
        return {
            "status": "ERROR",
            "error": "Design pressure must be greater than 0 MPa."
        }

    # 4. Fluid toxicity validation
    fluid_toxicity = fluid_toxicity.strip().lower()

    if not fluid_toxicity:
        return {
            "status": "ERROR",
            "error": "Fluid toxicity cannot be empty."
        }

    allowed_toxicity = {"low", "medium", "high"}

    if fluid_toxicity not in allowed_toxicity:
        return {
            "status": "ERROR",
            "error": "fluid_toxicity must be 'Low', 'Medium', or 'High'."
        }

    # 5. Critical condition check
    # Remaining life <= 0 indicates wall breach / unsafe condition
    if remaining_life_years <= 0:
        return {
            "risk_category": "CRITICAL_HIGH",
            "recommended_interval_months": 0,
            "statutory_verdict": "MANDATORY_IMMEDIATE_SHUTDOWN_INSPECTION"
        }

    # 6. Toxicity risk factor
    if fluid_toxicity == "high":
        toxicity_factor = 3
    elif fluid_toxicity == "medium":
        toxicity_factor = 2
    else:
        toxicity_factor = 1

    # 7. Pressure risk factor
    if design_pressure_mpa >= 15:
        pressure_factor = 3
    elif design_pressure_mpa >= 5:
        pressure_factor = 2
    else:
        pressure_factor = 1

    # 8. Remaining life risk factor
    if remaining_life_years <= 1:
        life_factor = 3
    elif remaining_life_years <= 3:
        life_factor = 2
    else:
        life_factor = 1

    # 9. Combined screening score
    risk_score = toxicity_factor + pressure_factor + life_factor

    # 10. Risk category and statutory interval assignment
    if risk_score >= 8:
        risk_category = "HIGH"
        recommended_interval_months = 6
        statutory_verdict = "ENGINEERING_REVIEW_REQUIRED"

    elif risk_score >= 6:
        risk_category = "MEDIUM_HIGH"
        recommended_interval_months = 12
        statutory_verdict = "ENHANCED_INSPECTION_REQUIRED"

    elif risk_score >= 4:
        risk_category = "MEDIUM"
        recommended_interval_months = 24
        statutory_verdict = "PERIODIC_INSPECTION_REQUIRED"

    else:
        risk_category = "LOW"
        recommended_interval_months = 36
        statutory_verdict = "ROUTINE_INSPECTION"

    return {
        "risk_category": risk_category,
        "recommended_interval_months": recommended_interval_months,
        "statutory_verdict": statutory_verdict
    }
