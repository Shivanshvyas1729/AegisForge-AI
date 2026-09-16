"""
tools/thickness_grid_analyzer.py
Multi-Point Ultrasonic Thickness Grid Assessment Engine.
Parses multi-coordinate inspection survey spreadsheets (.xlsx / .csv),
evaluates every survey point against ASME Section VIII Div 1 UG-27,
identifies governing critical locations, lists all breach coordinates,
and calculates the overall derated MAWP for the vessel.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.ug27_core import (
    validate_ug27_parameters,
    calculate_t_req,
    calculate_delta_margin,
    calculate_remaining_life,
    calculate_derated_mawp_bar,
)
from tools.file_io import _validate_safe_path
from tools.audit_trail import append_audit_event


def parse_thickness_grid(file_path: Path) -> List[Dict[str, Any]]:
    """
    Parses coordinate points from an Excel (.xlsx) or CSV file.
    Supports tabular lists [location, thickness] and 2D coordinate matrices.
    """
    points = []
    ext = file_path.suffix.lower()

    if ext == ".xlsx":
        import openpyxl
        wb = openpyxl.load_workbook(str(file_path), data_only=True)
        ws = wb.active

        # Scan for rows
        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise ValueError(f"Spreadsheet {file_path.name} contains no data rows.")

        header = [str(c).strip().lower() if c is not None else "" for c in rows[0]]
        
        # Check if tabular format with 'thickness' column
        thick_col_idx = None
        loc_col_idx = None
        for idx, col_name in enumerate(header):
            if "thick" in col_name or "actual" in col_name or "t_mm" in col_name or "meas" in col_name:
                thick_col_idx = idx
            elif "loc" in col_name or "point" in col_name or "coord" in col_name or "tag" in col_name or "id" in col_name:
                loc_col_idx = idx

        if thick_col_idx is not None:
            for r_idx, row in enumerate(rows[1:], start=2):
                val = row[thick_col_idx]
                if isinstance(val, (int, float)) and val > 0:
                    loc = str(row[loc_col_idx]) if loc_col_idx is not None and row[loc_col_idx] is not None else f"Point_{r_idx}"
                    points.append({"location": loc, "measured_thickness_mm": float(val)})
        else:
            # 2D Grid Matrix: row labels in col 0, column headers in row 0
            for r_idx, row in enumerate(rows[1:], start=1):
                row_label = str(row[0]).strip() if row[0] is not None else f"R{r_idx}"
                for c_idx, val in enumerate(row[1:], start=1):
                    if isinstance(val, (int, float)) and val > 0:
                        col_label = header[c_idx] if c_idx < len(header) and header[c_idx] else f"C{c_idx}"
                        coord = f"{row_label}-{col_label}"
                        points.append({"location": coord, "measured_thickness_mm": float(val)})

    elif ext == ".csv":
        import csv
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            reader = list(csv.reader(f))
            if not reader:
                raise ValueError(f"CSV file {file_path.name} is empty.")

            header = [c.strip().lower() for c in reader[0]]
            thick_col_idx = None
            loc_col_idx = None
            for idx, col_name in enumerate(header):
                if "thick" in col_name or "actual" in col_name or "t_mm" in col_name or "meas" in col_name:
                    thick_col_idx = idx
                elif "loc" in col_name or "point" in col_name or "coord" in col_name or "id" in col_name:
                    loc_col_idx = idx

            if thick_col_idx is not None:
                for r_idx, row in enumerate(reader[1:], start=2):
                    if len(row) > thick_col_idx:
                        try:
                            val = float(row[thick_col_idx])
                            loc = row[loc_col_idx] if loc_col_idx is not None and len(row) > loc_col_idx else f"Point_{r_idx}"
                            points.append({"location": loc, "measured_thickness_mm": val})
                        except ValueError:
                            pass
            else:
                for r_idx, row in enumerate(reader[1:], start=1):
                    if not row:
                        continue
                    row_label = row[0].strip() if row[0] else f"R{r_idx}"
                    for c_idx, val_str in enumerate(row[1:], start=1):
                        try:
                            val = float(val_str.strip())
                            col_label = header[c_idx] if c_idx < len(header) and header[c_idx] else f"C{c_idx}"
                            points.append({"location": f"{row_label}-{col_label}", "measured_thickness_mm": val})
                        except ValueError:
                            pass
    else:
        raise ValueError(f"Unsupported file format '{ext}'. Must be .xlsx or .csv.")

    if not points:
        raise ValueError(f"No valid numerical thickness coordinates could be extracted from {file_path.name}.")

    return points


def analyze_thickness_grid(
    file_path: str,
    design_pressure_mpa: float,
    inside_radius_mm: float,
    allowable_stress_mpa: float,
    joint_efficiency: float = 1.0,
    corrosion_allowance_mm: float = 0.0,
    corrosion_rate_mm_yr: float = 0.0,
) -> Dict[str, Any]:
    """
    Performs comprehensive ASME UG-27 evaluation across all coordinate points of a survey grid.
    All vessel design parameters are REQUIRED and strictly validated.
    """
    # Validate design parameters upfront
    validate_ug27_parameters(
        P=design_pressure_mpa,
        R=inside_radius_mm,
        S=allowable_stress_mpa,
        E=joint_efficiency,
        CA=corrosion_allowance_mm,
        CR=corrosion_rate_mm_yr
    )

    safe_path = _validate_safe_path(file_path)
    points = parse_thickness_grid(safe_path)

    t_req = calculate_t_req(
        P=design_pressure_mpa,
        R=inside_radius_mm,
        S=allowable_stress_mpa,
        E=joint_efficiency,
        CA=corrosion_allowance_mm
    )

    breached_points = []
    evaluated_points = []
    min_thickness = float("inf")
    worst_point = None

    for pt in points:
        t_meas = pt["measured_thickness_mm"]
        delta, is_breach, is_zero_margin = calculate_delta_margin(t_meas, t_req)

        eval_pt = {
            "location": pt["location"],
            "measured_thickness_mm": t_meas,
            "t_req_mm": t_req,
            "delta_mm": delta,
            "is_breach": is_breach,
        }
        evaluated_points.append(eval_pt)

        if is_breach:
            breached_points.append(eval_pt)

        if t_meas < min_thickness:
            min_thickness = t_meas
            worst_point = eval_pt

    # Overall vessel status
    has_breach = len(breached_points) > 0
    governing_mawp_bar = calculate_derated_mawp_bar(
        t_actual=worst_point["measured_thickness_mm"],
        CA=corrosion_allowance_mm,
        R=inside_radius_mm,
        S=allowable_stress_mpa,
        E=joint_efficiency
    )

    rem_life, life_status = calculate_remaining_life(
        t_actual=worst_point["measured_thickness_mm"],
        t_req=t_req,
        CR=corrosion_rate_mm_yr
    )

    return {
        "file_name": safe_path.name,
        "total_points_audited": len(points),
        "t_req_mm": t_req,
        "breached_points_count": len(breached_points),
        "breached_points": breached_points,
        "worst_location": worst_point["location"],
        "worst_measured_thickness_mm": worst_point["measured_thickness_mm"],
        "worst_delta_mm": worst_point["delta_mm"],
        "governing_status": "CRITICAL_BREACH" if has_breach else "SAFE",
        "governing_derated_mawp_bar": governing_mawp_bar,
        "api510_remaining_life_years": rem_life,
        "life_status": life_status,
    }


try:
    from langchain_core.tools import tool

    @tool
    def thickness_grid_tool(
        file_path: str,
        design_pressure_mpa: float,
        inside_radius_mm: float,
        allowable_stress_mpa: float,
        joint_efficiency: float = 1.0,
        corrosion_allowance_mm: float = 0.0,
        corrosion_rate_mm_yr: float = 0.0,
    ) -> str:
        """
        Analyzes a multi-point ultrasonic thickness survey spreadsheet (.xlsx or .csv).
        Evaluates ASME Section VIII Div 1 UG-27 on every coordinate point, locates the governing minimum,
        and computes derated MAWP.
        
        Args:
            file_path: Path to .xlsx or .csv thickness survey file [REQUIRED]
            design_pressure_mpa: Vessel design pressure in MPa [REQUIRED, > 0]
            inside_radius_mm: Inside shell radius in mm [REQUIRED, > 0]
            allowable_stress_mpa: Max allowable stress in MPa [REQUIRED, > 0]
            joint_efficiency: Weld joint efficiency (default 1.0, 0 < E <= 1.0)
            corrosion_allowance_mm: Corrosion allowance in mm (default 0.0, >= 0)
            corrosion_rate_mm_yr: Observed corrosion rate in mm/yr (default 0.0, >= 0)
        """
        start_time = time.time()
        inputs = {
            "file_path": file_path,
            "design_pressure_mpa": design_pressure_mpa,
            "inside_radius_mm": inside_radius_mm,
            "allowable_stress_mpa": allowable_stress_mpa,
            "joint_efficiency": joint_efficiency,
            "corrosion_allowance_mm": corrosion_allowance_mm,
            "corrosion_rate_mm_yr": corrosion_rate_mm_yr,
        }

        try:
            res = analyze_thickness_grid(
                file_path=file_path,
                design_pressure_mpa=design_pressure_mpa,
                inside_radius_mm=inside_radius_mm,
                allowable_stress_mpa=allowable_stress_mpa,
                joint_efficiency=joint_efficiency,
                corrosion_allowance_mm=corrosion_allowance_mm,
                corrosion_rate_mm_yr=corrosion_rate_mm_yr,
            )
            duration_ms = (time.time() - start_time) * 1000

            append_audit_event(
                tool_name="thickness_grid_tool",
                inputs=inputs,
                outputs=res,
                status="SUCCESS",
                duration_ms=duration_ms,
                caller="thickness_grid_tool"
            )

            breach_summary = ""
            if res["breached_points_count"] > 0:
                coords = [f"{p['location']} ({p['measured_thickness_mm']}mm, Δ={p['delta_mm']}mm)" for p in res["breached_points"][:5]]
                breach_summary = f"\n- Breached Coordinates ({res['breached_points_count']} total): {', '.join(coords)}"
                if res["breached_points_count"] > 5:
                    breach_summary += f" ... (+{res['breached_points_count'] - 5} more)"

            life_str = f"{res['api510_remaining_life_years']} years" if res['api510_remaining_life_years'] is not None else "N/A (Zero corrosion rate)"

            return (
                f"Multi-Point Thickness Grid Survey Audit for {res['file_name']}:\n"
                f"- Total Survey Points Audited: {res['total_points_audited']}\n"
                f"- ASME UG-27 Required Thickness (t_req): {res['t_req_mm']} mm\n"
                f"- Governing Critical Location: {res['worst_location']} "
                f"(Measured: {res['worst_measured_thickness_mm']} mm, Delta: {res['worst_delta_mm']} mm)\n"
                f"- Breached Points: {res['breached_points_count']} / {res['total_points_audited']}{breach_summary}\n"
                f"- Vessel Governing Status: {res['governing_status']}\n"
                f"- Governing Derated MAWP: {res['governing_derated_mawp_bar']} barg\n"
                f"- Governing API 510 Remaining Life: {life_str}"
            )

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            append_audit_event(
                tool_name="thickness_grid_tool",
                inputs=inputs,
                outputs={"error": str(e)},
                status="FAILURE",
                duration_ms=duration_ms,
                caller="thickness_grid_tool"
            )
            return f"Thickness Grid Analysis Error: {str(e)}"

except ImportError:
    thickness_grid_tool = None
