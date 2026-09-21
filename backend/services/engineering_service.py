"""
Engineering Mathematics & Integrity Assessment Service
======================================================
Deterministic ASME BPVC Sec VIII Div 1 UG-27, API 579 FFS, and Material Stress Lookups.
"""

from typing import Dict, Any, Optional
from tools.asme_calculator import calculate_asme_stresses, AsmeCalculator
from tools.api_579_ffs_tool import run_ffs_assessment
from tools.material_lookup_tool import lookup_material
from schemas.inspection import InspectionInput


class EngineeringService:
    """Service providing verifiable, deterministic engineering calculations."""

    def calculate_asme_ug27(
        self,
        design_pressure_mpa: float,
        inside_radius_mm: float,
        allowable_stress_mpa: float,
        joint_efficiency: float = 1.0,
        corrosion_allowance_mm: float = 0.0,
        measured_thickness_mm: float = 0.0,
        corrosion_rate_mm_yr: float = 0.5,
        equipment_id: str = "VESSEL-001"
    ) -> Dict[str, Any]:
        """
        Calculates required wall thickness and safety margins according to ASME Sec VIII Div 1 UG-27:
        t_req = (P * R) / (S * E - 0.6 * P) + CA
        """
        return calculate_asme_stresses.invoke({
            "design_pressure_mpa": float(design_pressure_mpa),
            "inside_radius_mm": float(inside_radius_mm),
            "allowable_stress_mpa": float(allowable_stress_mpa),
            "joint_efficiency": float(joint_efficiency),
            "corrosion_allowance_mm": float(corrosion_allowance_mm),
            "measured_thickness_mm": float(measured_thickness_mm),
            "corrosion_rate_mm_yr": float(corrosion_rate_mm_yr),
            "equipment_id": str(equipment_id)
        })

    def run_ffs_assessment(
        self,
        equipment_id: str,
        t_min_measured_mm: float,
        t_nominal_mm: float,
        design_pressure_mpa: float,
        inside_radius_mm: float,
        allowable_stress_mpa: float,
        joint_efficiency: float = 1.0,
        assessment_level: int = 1
    ) -> Dict[str, Any]:
        """
        Runs API 579-1/ASME FFS-1 Fitness-For-Service Part 5 (Local Thin Area / Metal Loss).
        Computes Remaining Strength Factor (RSF) and derated MAWP.
        """
        return run_ffs_assessment.invoke({
            "equipment_id": equipment_id,
            "t_min_measured_mm": t_min_measured_mm,
            "t_nominal_mm": t_nominal_mm,
            "design_pressure_mpa": design_pressure_mpa,
            "inside_radius_mm": inside_radius_mm,
            "allowable_stress_mpa": allowable_stress_mpa,
            "joint_efficiency": joint_efficiency,
            "assessment_level": assessment_level
        })

    def lookup_material_stress(
        self,
        material_grade: str,
        temperature_c: float = 350.0
    ) -> Dict[str, Any]:
        """
        Looks up ASME Section II Part D allowable stresses for pressure vessel steels across temperature curves.
        """
        return lookup_material.invoke({
            "material_grade": material_grade,
            "temperature_c": float(temperature_c)
        })
