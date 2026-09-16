"""
tools/ug27_core.py
Single Source of Truth for ASME Section VIII Div 1 UG-27 and API 510 Engineering Calculations.
Provides validated, centralized mathematical functions for minimum required shell thickness,
safety margins, API 510 remaining service life, and derated Maximum Allowable Working Pressure (MAWP).
"""

from typing import Tuple, Optional


def validate_ug27_parameters(
    P: float,
    R: float,
    S: float,
    E: float,
    CA: float,
    t_actual: Optional[float] = None,
    CR: Optional[float] = None,
) -> None:
    """
    Validates physical parameters against ASME Section VIII Div 1 UG-27 boundary conditions.
    Raises ValueError with explicit diagnostic messages on any violation.
    """
    if P <= 0:
        raise ValueError(f"Invalid design pressure P={P} MPa: Pressure must be strictly positive (> 0).")
    if R <= 0:
        raise ValueError(f"Invalid inside radius R={R} mm: Radius must be strictly positive (> 0).")
    if S <= 0:
        raise ValueError(f"Invalid allowable stress S={S} MPa: Stress must be strictly positive (> 0).")
    if not (0.0 < E <= 1.0):
        raise ValueError(f"Invalid joint efficiency E={E}: Efficiency must be in the range (0.0, 1.0].")
    if CA < 0:
        raise ValueError(f"Invalid corrosion allowance CA={CA} mm: Allowance cannot be negative.")

    denominator = (S * E) - (0.6 * P)
    if denominator <= 0:
        raise ValueError(
            f"Invalid ASME UG-27 geometry: S*E - 0.6*P = {denominator:.4f} <= 0. "
            f"Design pressure {P} MPa exceeds structural capacity of material S={S} MPa with efficiency E={E}."
        )

    if t_actual is not None and t_actual <= 0:
        raise ValueError(f"Invalid measured thickness t_actual={t_actual} mm: Thickness must be strictly positive (> 0).")

    if CR is not None and CR < 0:
        raise ValueError(f"Invalid corrosion rate CR={CR} mm/yr: Corrosion rate cannot be negative.")


def calculate_t_req(
    P: float,
    R: float,
    S: float,
    E: float,
    CA: float,
) -> float:
    """
    Computes minimum required shell thickness t_req under ASME Section VIII Div 1 UG-27 (cylindrical shell):
        t_req = (P * R) / (S * E - 0.6 * P) + CA

    Args:
        P: Design internal pressure in MPa
        R: Inside radius of shell in mm
        S: Maximum allowable stress in MPa
        E: Joint efficiency (0.0 < E <= 1.0)
        CA: Corrosion allowance in mm

    Returns:
        Minimum required thickness rounded to 2 decimal places.
    """
    validate_ug27_parameters(P=P, R=R, S=S, E=E, CA=CA)
    denominator = (S * E) - (0.6 * P)
    t_pressure = (P * R) / denominator
    return round(t_pressure + CA, 2)


def calculate_delta_margin(
    t_actual: float,
    t_req: float,
) -> Tuple[float, bool, bool]:
    """
    Computes delta margin between measured thickness and ASME code minimum:
        delta = t_actual - t_req

    Zero Margin Decision:
        - When delta < 0.0: Statutory breach detected (is_breach = True).
        - When delta == 0.0: Exactly at minimum code limit (is_breach = False, is_zero_margin = True).
        - When delta > 0.0: Compliant with positive margin (is_breach = False, is_zero_margin = False).

    Returns:
        Tuple of (delta_mm, is_breach, is_zero_margin)
    """
    if t_actual <= 0:
        raise ValueError(f"Measured thickness {t_actual} mm must be strictly positive.")
    if t_req <= 0:
        raise ValueError(f"Required thickness {t_req} mm must be strictly positive.")

    delta = round(t_actual - t_req, 2)
    is_breach = delta < 0.0
    is_zero_margin = delta == 0.0
    return delta, is_breach, is_zero_margin


def calculate_remaining_life(
    t_actual: float,
    t_req: float,
    CR: float,
) -> Tuple[Optional[float], str]:
    """
    Computes API 510 remaining service life:
        Remaining Life = (t_actual - t_req) / CR

    Zero-Corrosion Guard:
        If CR == 0.0 mm/yr (e.g. non-corrosive / dry service), division by zero is guarded
        and returns (None, "N/A (No active corrosion detected)").

    Returns:
        Tuple of (remaining_life_years: Optional[float], status_label: str)
    """
    if t_actual <= 0 or t_req <= 0:
        raise ValueError("Both t_actual and t_req must be strictly positive.")
    if CR < 0:
        raise ValueError(f"Corrosion rate {CR} mm/yr cannot be negative.")

    if CR == 0.0:
        return None, "N/A (No active corrosion detected)"

    life = round((t_actual - t_req) / CR, 2)
    return life, "ACTIVE"


def calculate_derated_mawp_bar(
    t_actual: float,
    CA: float,
    R: float,
    S: float,
    E: float,
) -> float:
    """
    Computes derated Maximum Allowable Working Pressure (MAWP) in barg for corroded cylindrical shell
    in accordance with ASME Section VIII Div 1 UG-27 and API 510 Section 7:

        t_available = max(0.0, t_actual - CA)
        MAWP_mpa = (S * E * t_available) / (R + 0.6 * t_available)
        MAWP_bar = round(MAWP_mpa * 10.0, 1)

    t_available is explicitly defined as the effective remaining metal thickness
    available for pressure containment after future corrosion allowance is accounted for.

    Returns:
        Derated MAWP in bar (gauge) rounded to 1 decimal place.
    """
    if t_actual <= 0:
        raise ValueError(f"Measured thickness {t_actual} mm must be positive.")
    if R <= 0 or S <= 0 or not (0.0 < E <= 1.0) or CA < 0:
        raise ValueError("Invalid physical parameters for MAWP derating.")

    t_available = max(0.0, t_actual - CA)
    if t_available <= 0.0:
        return 0.0

    denominator = R + (0.6 * t_available)
    mawp_mpa = (S * E * t_available) / denominator
    return round(mawp_mpa * 10.0, 1)
