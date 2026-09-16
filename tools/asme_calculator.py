"""
tools/asme_calculator.py
ASME Section VIII Div 1 UG-27 & API 510 Integrity Assessment Engine.
Refactored to delegate all mathematical operations to tools/ug27_core.py.
Enforces strict parameter validation, eliminates silent dummy defaults,
and logs all calculations to the sovereign audit ledger.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from schemas.mvp_schema import InspectionInput, CalculationOutput
from tools.ug27_core import (
    validate_ug27_parameters,
    calculate_t_req,
    calculate_delta_margin,
    calculate_remaining_life,
    calculate_derated_mawp_bar,
)
from tools.audit_trail import append_audit_event


def evaluate_vessel_integrity(inp: InspectionInput) -> CalculationOutput:
    """
    Evaluates pressure vessel integrity against ASME Section VIII Div 1 UG-27
    and API 510 remaining service life using the centralized math core.
    """
    P = inp.design_pressure_mpa
    R = inp.inside_radius_mm
    S = inp.allowable_stress_mpa
    E = inp.joint_efficiency
    CA = inp.corrosion_allowance_mm
    t_actual = inp.measured_thickness_mm
    CR = inp.corrosion_rate_mm_yr

    # 1. Compute minimum required thickness (automatically validates inputs)
    t_req = calculate_t_req(P=P, R=R, S=S, E=E, CA=CA)

    # 2. Compute safety margin delta
    delta, is_breach, is_zero_margin = calculate_delta_margin(t_actual=t_actual, t_req=t_req)

    # 3. Compute API 510 remaining life with zero-corrosion guard
    remaining_life, life_status = calculate_remaining_life(t_actual=t_actual, t_req=t_req, CR=CR)

    # 4. Compute derated MAWP in barg
    derated_mawp_bar = calculate_derated_mawp_bar(t_actual=t_actual, CA=CA, R=R, S=S, E=E)

    design_bar = round(P * 10.0, 1)

    if is_breach:
        status = "CRITICAL_BREACH"
    elif is_zero_margin:
        status = "MARGINAL_ALERT (ZERO SAFETY MARGIN - REVIEW REQUIRED)"
    else:
        status = "SAFE"

    return CalculationOutput(
        t_req_mm=t_req,
        measured_thickness_mm=t_actual,
        delta_mm=delta,
        is_breach=is_breach,
        remaining_life_years=remaining_life,
        derated_mawp_bar=derated_mawp_bar,
        design_pressure_bar=design_bar,
        status=status,
        formula_used="t_req = (P * R) / (S * E - 0.6 * P) + CA"
    )


try:
    from langchain_core.tools import tool

    @tool
    def asme_calc_tool(
        equipment_id: str,
        design_pressure_mpa: float,
        inside_radius_mm: float,
        allowable_stress_mpa: float,
        measured_thickness_mm: float,
        joint_efficiency: float = 1.0,
        corrosion_allowance_mm: float = 0.0,
        corrosion_rate_mm_yr: float = 0.0,
    ) -> str:
        """
        Calculates ASME Section VIII Div 1 UG-27 minimum shell thickness,
        delta margin, derated MAWP, and API 510 remaining safe life for pressure vessels.
        
        Args:
            equipment_id: Vessel tag identifier (e.g. '11-V-102') [REQUIRED]
            design_pressure_mpa: Internal design pressure in MPa [REQUIRED, > 0]
            inside_radius_mm: Shell inside radius in mm [REQUIRED, > 0]
            allowable_stress_mpa: Allowable stress in MPa [REQUIRED, > 0]
            measured_thickness_mm: Current measured shell thickness in mm [REQUIRED, > 0]
            joint_efficiency: Weld joint efficiency (default 1.0, 0 < E <= 1.0)
            corrosion_allowance_mm: Corrosion allowance in mm (default 0.0, >= 0)
            corrosion_rate_mm_yr: Corrosion rate in mm/yr (default 0.0, >= 0)
        """
        start_time = time.time()
        inputs = {
            "equipment_id": equipment_id,
            "design_pressure_mpa": design_pressure_mpa,
            "inside_radius_mm": inside_radius_mm,
            "allowable_stress_mpa": allowable_stress_mpa,
            "measured_thickness_mm": measured_thickness_mm,
            "joint_efficiency": joint_efficiency,
            "corrosion_allowance_mm": corrosion_allowance_mm,
            "corrosion_rate_mm_yr": corrosion_rate_mm_yr,
        }

        try:
            inp = InspectionInput(
                equipment_id=equipment_id,
                design_pressure_mpa=design_pressure_mpa,
                inside_radius_mm=inside_radius_mm,
                allowable_stress_mpa=allowable_stress_mpa,
                joint_efficiency=joint_efficiency,
                corrosion_allowance_mm=corrosion_allowance_mm,
                measured_thickness_mm=measured_thickness_mm,
                corrosion_rate_mm_yr=corrosion_rate_mm_yr,
            )
            res = evaluate_vessel_integrity(inp)
            duration_ms = (time.time() - start_time) * 1000

            outputs = {
                "t_req_mm": res.t_req_mm,
                "measured_thickness_mm": res.measured_thickness_mm,
                "delta_mm": res.delta_mm,
                "is_breach": res.is_breach,
                "remaining_life_years": res.remaining_life_years,
                "derated_mawp_bar": res.derated_mawp_bar,
                "status": res.status,
            }

            append_audit_event(
                tool_name="asme_calc_tool",
                inputs=inputs,
                outputs=outputs,
                status="SUCCESS",
                duration_ms=duration_ms,
                caller="asme_calc_tool"
            )

            life_str = f"{res.remaining_life_years} years" if res.remaining_life_years is not None else "N/A (Zero corrosion rate)"

            return (
                f"ASME Section VIII Div 1 UG-27 Integrity Assessment for {equipment_id}:\n"
                f"- Required Minimum Thickness (t_req): {res.t_req_mm} mm\n"
                f"- Measured Thickness: {res.measured_thickness_mm} mm\n"
                f"- Safety Margin Delta (t_actual - t_req): {res.delta_mm} mm\n"
                f"- Assessment Status: {res.status}\n"
                f"- API 510 Remaining Safe Life: {life_str}\n"
                f"- Original Design Pressure: {res.design_pressure_bar} barg\n"
                f"- Derated MAWP: {res.derated_mawp_bar} barg\n"
                f"- Governing Formula: {res.formula_used}"
            )
        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            append_audit_event(
                tool_name="asme_calc_tool",
                inputs=inputs,
                outputs={"error": str(e)},
                status="FAILURE",
                duration_ms=duration_ms,
                caller="asme_calc_tool"
            )
            return f"ASME Calculation Error: {str(e)}"

except ImportError:
    asme_calc_tool = None
