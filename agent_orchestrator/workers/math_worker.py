"""
agent_orchestrator/workers/math_worker.py
Math Worker Node (Deterministic Engineering Calculation Controller).
Uses Qwen2.5-Coder for tool dispatch supervision and executes pure ASME Section VIII Div 1
UG-27 / API 510 calculations via centralized ug27_core / asme_calculator.
Enforces strict tool passthrough: NEVER permits local LLMs to perform arithmetic or override code math.
"""

import sys
from pathlib import Path
from typing import Dict, Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from agent_orchestrator.state import MultiAgentSystemState
from schemas.mvp_schema import InspectionInput, CalculationOutput
from tools.asme_calculator import evaluate_vessel_integrity
from tools.thickness_grid_analyzer import analyze_thickness_grid
from tools.audit_trail import append_audit_event
from config.settings import logger


def math_worker_node(state: MultiAgentSystemState) -> MultiAgentSystemState:
    """
    Math Worker: Extracts confirmed parameters, validates completeness,
    and delegates to deterministic ASME Section VIII / API 510 tools.
    """
    inspection_data = state.get("inspection_data", {})
    params = inspection_data.get("extracted_parameters", {})

    logger.info(f"[MathWorker] Executing deterministic ASME calculation for: {params.get('equipment_id', 'UNKNOWN')}")

    # Check if a grid file was provided
    grid_file = params.get("grid_file_path") or state.get("uploaded_file_path")
    if grid_file and str(grid_file).lower().endswith((".xlsx", ".csv")):
        logger.info(f"[MathWorker] Detected thickness grid survey: {grid_file}")
        grid_res = analyze_thickness_grid(
            file_path=grid_file,
            design_pressure_mpa=float(params.get("design_pressure_mpa", 14.5)),
            inside_radius_mm=float(params.get("inside_radius_mm", 1200.0)),
            allowable_stress_mpa=float(params.get("allowable_stress_mpa", 138.0)),
            joint_efficiency=float(params.get("joint_efficiency", 1.0)),
            corrosion_allowance_mm=float(params.get("corrosion_allowance_mm", 4.0)),
            corrosion_rate_mm_yr=float(params.get("corrosion_rate_mm_yr", 0.75)),
        )
        state["calculation_data"] = grid_res
        calc_summary = {
            "t_req_mm": grid_res.get("t_req_mm"),
            "worst_location": grid_res.get("worst_location"),
            "min_thickness_mm": grid_res.get("min_thickness_mm"),
            "status": grid_res.get("overall_status"),
        }
    else:
        # Single-point vessel integrity assessment
        inp = InspectionInput(
            equipment_id=str(params.get("equipment_id", "VESSEL-001")),
            equipment_name=str(params.get("equipment_name", "Pressure Vessel")),
            critical_location=str(params.get("critical_location", "Shell / Head")),
            material=str(params.get("material", "Carbon / Alloy Steel")),
            design_pressure_mpa=float(params["design_pressure_mpa"]),
            inside_radius_mm=float(params["inside_radius_mm"]),
            allowable_stress_mpa=float(params["allowable_stress_mpa"]),
            measured_thickness_mm=float(params["measured_thickness_mm"]),
            joint_efficiency=float(params["joint_efficiency"]),
            corrosion_allowance_mm=float(params["corrosion_allowance_mm"]),
            corrosion_rate_mm_yr=float(params.get("corrosion_rate_mm_yr", 0.0)),
            inspector_notes=str(params.get("inspector_notes", "Automated extraction")),
        )

        calc_result: CalculationOutput = evaluate_vessel_integrity(inp)
        calc_dict = calc_result.model_dump()
        state["calculation_data"] = calc_dict
        calc_summary = {
            "t_req_mm": calc_result.t_req_mm,
            "measured_thickness_mm": calc_result.measured_thickness_mm,
            "delta_mm": calc_result.delta_mm,
            "status": calc_result.status,
            "remaining_life_years": calc_result.remaining_life_years,
            "derated_mawp_bar": calc_result.derated_mawp_bar,
        }

    logger.info(f"[MathWorker] Calculation completed: status={calc_summary.get('status')}")

    entry_hash = append_audit_event(
        tool_name="math_worker_node",
        inputs={"equipment_id": params.get("equipment_id")},
        outputs=calc_summary,
        status="CALCULATION_SUCCESS",
        caller="math_worker_node"
    )
    state.setdefault("audit_trail_events", []).append(entry_hash)

    return state
