"""
tools/asme_calculator.py
Layer 4 / Tools: ASME Code Engineering Math Verification Engine (Member 3).
Computes ASME Section VIII Div 1 UG-27 cylindrical shell minimum thickness (t_min),
evaluates safety breach margin (delta), and computes API 510 remaining life.
"""

import sys
from pathlib import Path

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from schemas.mvp_schema import InspectionInput, CalculationOutput


def evaluate_vessel_integrity(inp: InspectionInput) -> CalculationOutput:
    """
    Evaluates pressure vessel integrity against ASME Section VIII Div 1 UG-27.
    Formula:
        t_req = (P * R) / (S * E - 0.6 * P) + CA
    """
    P = inp.design_pressure_mpa
    R = inp.inside_radius_mm
    S = inp.allowable_stress_mpa
    E = inp.joint_efficiency
    CA = inp.corrosion_allowance_mm
    t_actual = inp.measured_thickness_mm
    CR = inp.corrosion_rate_mm_yr

    # 1. Compute ASME Section VIII Div 1 UG-27 minimum required thickness
    denominator = (S * E) - (0.6 * P)
    if denominator <= 0:
        raise ValueError("Invalid parameters: S*E - 0.6*P must be greater than zero.")
    
    t_pressure = (P * R) / denominator
    t_req = round(t_pressure + CA, 2)

    # 2. Compute safety margin delta (t_actual - t_req)
    delta = round(t_actual - t_req, 2)
    is_breach = delta < 0

    # 3. Compute API 510 Remaining Service Life in years
    # Life = (t_actual - t_req) / Corrosion_Rate
    if CR > 0:
        remaining_life = round((t_actual - t_req) / CR, 2)
    else:
        remaining_life = 99.0

    # 4. Compute derated Maximum Allowable Working Pressure (MAWP)
    # MAWP = (S * E * t_corroded) / (R + 0.6 * t_corroded)
    t_available = max(0.1, t_actual - CA)
    mawp_mpa = (S * E * t_available) / (R + 0.6 * t_available)
    derated_mawp_bar = round(mawp_mpa * 10, 1)  # 1 MPa = 10 bar

    # Convert design pressure to bar
    design_bar = round(P * 10, 1)

    status = "CRITICAL_BREACH" if is_breach else "SAFE"

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
        equipment_id: str = "11-V-102",
        design_pressure_mpa: float = 14.5,
        inside_radius_mm: float = 1200.0,
        allowable_stress_mpa: float = 138.0,
        joint_efficiency: float = 1.0,
        corrosion_allowance_mm: float = 4.0,
        measured_thickness_mm: float = 138.20,
        corrosion_rate_mm_yr: float = 0.75,
    ) -> str:
        """
        Calculates ASME Section VIII Div 1 UG-27 minimum shell thickness,
        delta margin, and API 510 remaining safe life for pressure vessels.
        """
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
        return (
            f"ASME Section VIII Div 1 UG-27 Evaluation for {equipment_id}:\n"
            f"- Required t_min: {res.t_req_mm} mm\n"
            f"- Actual measured thickness: {res.measured_thickness_mm} mm\n"
            f"- Delta margin: {res.delta_mm} mm\n"
            f"- Breach status: {'BREACH DETECTED' if res.is_breach else 'SAFE'}\n"
            f"- API 510 Remaining safe life: {res.remaining_life_years} years\n"
            f"- Derated MAWP: {res.derated_mawp_bar} barg"
        )
except ImportError:
    asme_calc_tool = None


if __name__ == "__main__":
    test_input = InspectionInput(
        equipment_id="11-V-102",
        equipment_name="HP Separator drum",
        material="2.25Cr-1Mo",
        design_pressure_mpa=14.5,
        inside_radius_mm=1200.0,
        allowable_stress_mpa=138.0,
        joint_efficiency=1.0,
        corrosion_allowance_mm=4.0,
        critical_location="BK-01",
        measured_thickness_mm=138.20,
        corrosion_rate_mm_yr=0.75,
    )

    print("Testing ASME Calculator on 11-V-102 baseline...")
    res = evaluate_vessel_integrity(test_input)

    print("\n--- ASME Code Verification Output ---")
    print(f"Formula:          {res.formula_used}")
    print(f"Required t_min:   {res.t_req_mm} mm")
    print(f"Actual Thickness: {res.measured_thickness_mm} mm")
    print(f"Delta:            {res.delta_mm} mm")
    print(f"Is Breach:        {res.is_breach}")
    print(f"Remaining Life:   {res.remaining_life_years} Years")
    print(f"Design Pressure:  {res.design_pressure_bar} barg")
    print(f"Derated MAWP:     {res.derated_mawp_bar} barg")
    print(f"Status:           {res.status}")
    print("-" * 50)

    assert res.t_req_mm == 138.57, f"Expected 138.57, got {res.t_req_mm}"
    assert res.delta_mm == -0.37, f"Expected -0.37, got {res.delta_mm}"
    assert res.is_breach is True, "Expected is_breach == True"
    print("✅ ASME Calculator DoD PASSED!")
