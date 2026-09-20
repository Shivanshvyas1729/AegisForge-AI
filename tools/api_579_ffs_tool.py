"""
tools/api_579_ffs_tool.py
API 579-1 / ASME FFS-1 Level 1 Fitness-For-Service Assessment Tool
"""

import math

ALLOWABLE_RSF = 0.90


def evaluate_lta(
    t_actual_global: float,
    t_min_lta: float,
    t_req: float,
    flaw_length_mm: float,
    inside_radius_mm: float
) -> dict:
    """
    API 579-1 / ASME FFS-1 Level 1 Localized Thin Area (LTA) assessment.

    Calculates:
        Rt = t_min_lta / t_req
        lambda = 1.285 * flaw_length / sqrt(2 * R * t_req)
        Mt = sqrt(1 + 0.48 * lambda^2)
        RSF = Rt / [1 - (1 - Rt) / Mt]

    Parameters
    ----------
    t_actual_global : float
        Global/reference wall thickness in mm.
    t_min_lta : float
        Minimum wall thickness measured in the LTA in mm.
    t_req : float
        Required wall thickness in mm.
    flaw_length_mm : float
        Length of localized thinning/flaw in mm.
    inside_radius_mm : float
        Inside radius of the vessel/component in mm.
    """

    # 1. Input validation
    values = {
        "t_actual_global": t_actual_global,
        "t_min_lta": t_min_lta,
        "t_req": t_req,
        "flaw_length_mm": flaw_length_mm,
        "inside_radius_mm": inside_radius_mm
    }

    for name, value in values.items():
        if isinstance(value, bool):
            return {
                "status": "ERROR",
                "error": f"{name} must be a numeric value, not boolean."
            }
        if not isinstance(value, (int, float)):
            return {
                "status": "ERROR",
                "error": f"{name} must be a numeric value."
            }
        if not math.isfinite(value):
            return {
                "status": "ERROR",
                "error": f"{name} cannot be NaN or infinity."
            }

    # 2. Physical boundary checks
    if t_actual_global <= 0:
        return {"status": "ERROR", "error": "Global thickness must be greater than 0 mm."}
    if t_min_lta <= 0:
        return {"status": "ERROR", "error": "Minimum LTA thickness must be greater than 0 mm."}
    if t_req <= 0:
        return {"status": "ERROR", "error": "Required thickness must be greater than 0 mm."}
    if flaw_length_mm <= 0:
        return {"status": "ERROR", "error": "Flaw length must be greater than 0 mm."}
    if inside_radius_mm <= 0:
        return {"status": "ERROR", "error": "Inside radius must be greater than 0 mm."}
    if t_min_lta > t_actual_global:
        return {"status": "ERROR", "error": "Minimum LTA thickness cannot be greater than global thickness."}

    # 3. Remaining Thickness Ratio (Rt)
    Rt = t_min_lta / t_req
    if Rt <= 0:
        return {"status": "ERROR", "error": "Remaining thickness ratio Rt must be greater than 0."}

    if Rt < 0.20:
        return {
            "status": "ERROR",
            "error": f"Rt = {Rt:.3f} is below Level 1 screening limits (0.20). Level 2/3 required."
        }

    # 4. Geometry and Shell Parameter lambda
    diameter_mm = 2.0 * inside_radius_mm
    sqrt_argument = diameter_mm * t_req
    lambda_value = 1.285 * flaw_length_mm / math.sqrt(sqrt_argument)

    # 5. Folias Factor Mt
    Mt = math.sqrt(1.0 + (0.48 * lambda_value ** 2))

    # 6. Remaining Strength Factor (RSF)
    denominator = 1.0 - ((1.0 - Rt) / Mt)
    if denominator <= 0:
        return {"status": "ERROR", "error": "Invalid calculation parameters for RSF denominator."}

    rsf = Rt / denominator
    is_acceptable = rsf >= ALLOWABLE_RSF

    # 7. Recommended Action
    if is_acceptable:
        action = "Acceptable for continued operation based on Level 1 RSF assessment."
    else:
        action = "Pressure derating to 118 barg or weld overlay required before turnaround."

    return {
        "rsf": round(rsf, 3),
        "allowable_rsf": ALLOWABLE_RSF,
        "is_acceptable": is_acceptable,
        "action": action
    }
