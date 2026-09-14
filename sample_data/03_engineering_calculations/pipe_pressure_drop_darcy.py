"""
================================================================================
ENGINEERING CALCULATION MODULE: HYDRAULIC PRESSURE DROP & PIPE SIZING
Standard: Darcy-Weisbach Equation & Colebrook-White Friction Factor
Facility: Guwahati Refinery - Crude Distillation Unit (CDU-1)
Service: Light Gas Oil (LGO) Run-down Line to Storage
================================================================================
"""

import math
from typing import Dict, Any


def calculate_reynolds_number(velocity: float, inner_diameter: float, density: float, dynamic_viscosity: float) -> float:
    """
    Calculate dimensionless Reynolds Number (Re).
    Re = (rho * v * D) / mu
    """
    reynolds = (density * velocity * inner_diameter) / dynamic_viscosity
    return reynolds


def calculate_darcy_friction_factor(reynolds: float, roughness: float, inner_diameter: float, tolerance: float = 1e-6) -> float:
    """
    Calculate Darcy friction factor (f) using Colebrook-White implicit equation:
    1 / sqrt(f) = -2.0 * log10( (epsilon / (3.7 * D)) + (2.51 / (Re * sqrt(f))) )
    Solves via Newton-Raphson iteration.
    """
    if reynolds < 2300:
        # Laminar flow regime
        return 64.0 / reynolds

    # Relative roughness
    rel_roughness = roughness / inner_diameter

    # Initial guess using Swamee-Jain explicit approximation
    f = 0.25 / (math.log10((rel_roughness / 3.7) + (5.74 / (reynolds ** 0.9)))) ** 2

    # Newton-Raphson iteration for high precision Colebrook solution
    for _ in range(100):
        sqrt_f = math.sqrt(f)
        arg = (rel_roughness / 3.7) + (2.51 / (reynolds * sqrt_f))
        if arg <= 0:
            break
        # Function: F(f) = 1/sqrt(f) + 2*log10(arg) = 0
        func = (1.0 / sqrt_f) + 2.0 * math.log10(arg)
        # Derivative dF/df
        d_func = -0.5 * (f ** -1.5) + (2.0 / (math.log(10.0) * arg)) * (-1.255 / (reynolds * (f ** 1.5)))
        f_next = f - (func / d_func)
        if abs(f_next - f) < tolerance:
            f = f_next
            break
        f = f_next

    return f


def calculate_pressure_drop(
    flow_rate_m3h: float,
    pipe_nominal_dn: int,
    pipe_schedule: str,
    pipe_length_m: float,
    equivalent_length_fittings_m: float,
    density_kg_m3: float,
    viscosity_cp: float,
    pipe_roughness_mm: float = 0.0457,  # Commercial steel pipe per API 14E
    elevation_change_m: float = 0.0
) -> Dict[str, Any]:
    """
    Execute end-to-end Darcy-Weisbach pressure drop calculations for industrial pipeline.
    """
    # Pipe dimensions standard: ASME B36.10M
    # DN150 (6") Sch 40 standard internal diameter = 154.05 mm
    pipe_id_map = {
        (150, "40"): 0.15405,  # 6-inch Sch 40 (m)
        (200, "40"): 0.20272,  # 8-inch Sch 40 (m)
        (250, "40"): 0.25446,  # 10-inch Sch 40 (m)
    }

    key = (pipe_nominal_dn, pipe_schedule)
    if key not in pipe_id_map:
        raise ValueError(f"Pipe size DN{pipe_nominal_dn} Sch {pipe_schedule} not in database.")

    inner_diameter = pipe_id_map[key]
    pipe_area = (math.pi / 4.0) * (inner_diameter ** 2)

    # Volumetric and mass flow rate conversions
    q_m3_s = flow_rate_m3h / 3600.0
    mass_flow_kg_s = q_m3_s * density_kg_m3

    # Fluid velocity (m/s)
    velocity = q_m3_s / pipe_area

    # Dynamic viscosity in Pa.s (1 cP = 1e-3 Pa.s)
    viscosity_pa_s = viscosity_cp * 1e-3

    # Hydrodynamic parameters
    reynolds = calculate_reynolds_number(velocity, inner_diameter, density_kg_m3, viscosity_pa_s)
    roughness_m = pipe_roughness_mm * 1e-3
    friction_factor = calculate_darcy_friction_factor(reynolds, roughness_m, inner_diameter)

    # Total effective length including valves and fittings
    total_length = pipe_length_m + equivalent_length_fittings_m

    # Darcy-Weisbach frictional head loss (h_f = f * (L/D) * (v^2 / (2g)))
    g = 9.80665  # m/s^2
    frictional_head_loss_m = friction_factor * (total_length / inner_diameter) * (velocity ** 2) / (2.0 * g)
    
    # Frictional pressure drop Delta P = rho * g * h_f (Pascals)
    delta_p_friction_pa = density_kg_m3 * g * frictional_head_loss_m
    delta_p_friction_bar = delta_p_friction_pa / 1e5

    # Static elevation head Delta P_elev = rho * g * Delta z
    delta_p_elev_bar = (density_kg_m3 * g * elevation_change_m) / 1e5

    # Total pressure drop
    total_delta_p_bar = delta_p_friction_bar + delta_p_elev_bar

    # Specific pressure drop (bar per 100 meters)
    dp_per_100m = (delta_p_friction_bar / total_length) * 100.0

    return {
        "fluid": "Light Gas Oil (LGO)",
        "nominal_diameter_mm": pipe_nominal_dn,
        "internal_diameter_mm": round(inner_diameter * 1000, 2),
        "flow_rate_m3_hr": flow_rate_m3h,
        "flow_velocity_m_s": round(velocity, 3),
        "reynolds_number": round(reynolds, 1),
        "flow_regime": "Turbulent" if reynolds > 4000 else "Laminar",
        "darcy_friction_factor": round(friction_factor, 5),
        "total_piping_effective_length_m": total_length,
        "frictional_pressure_drop_bar": round(delta_p_friction_bar, 4),
        "elevation_pressure_drop_bar": round(delta_p_elev_bar, 4),
        "total_pressure_drop_bar": round(total_delta_p_bar, 4),
        "pressure_drop_rate_bar_per_100m": round(dp_per_100m, 4),
        "velocity_compliance_api14e": "PASS (< 3.0 m/s for refinery hydrocarbons)" if velocity <= 3.0 else "FAIL (Erosion Risk)"
    }


if __name__ == "__main__":
    # Test case: 180 m3/hr Light Gas Oil through 6" Sch 40 line, 450m length, 12m lift
    results = calculate_pressure_drop(
        flow_rate_m3h=180.0,
        pipe_nominal_dn=150,
        pipe_schedule="40",
        pipe_length_m=450.0,
        equivalent_length_fittings_m=85.0,
        density_kg_m3=845.0,
        viscosity_cp=2.8,
        elevation_change_m=12.0
    )

    print("=" * 60)
    print("REFINERY PIPELINE HYDRAULIC PRESSURE DROP REPORT")
    print("=" * 60)
    for key, value in results.items():
        print(f"  {key:<35}: {value}")
    print("=" * 60)
