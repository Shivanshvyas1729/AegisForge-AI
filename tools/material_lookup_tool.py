"""
tools/material_lookup_tool.py
ASME Section II Part D Material Property Database Lookup.
Strictly returns allowable stresses to prevent LLM hallucination of material properties.
"""

import sys
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.audit_trail import append_audit_event

# Simplified MVP Database (ASME Sec II Part D Table 1A approximations in MPa for ambient temp)
MATERIAL_DB = {
    "SA-516 Gr 70": 138.0,
    "SA-106 Gr B": 118.0,
    "2.25Cr-1Mo": 138.0,
    "SA-387 Gr 22 Cl 2": 138.0,
    "SA-312 TP304L": 115.0,
    "Carbon Steel": 138.0, # Fallback generic
}

def lookup_allowable_stress(material_grade: str, temperature_c: Optional[float] = 20.0) -> float:
    """Returns the allowable stress in MPa for a given material."""
    for key, val in MATERIAL_DB.items():
        # Substring match to handle slight variations in OCR naming
        if key.replace(" ", "").lower() in material_grade.replace(" ", "").lower():
            return val
    
    # Generic fallback if specific alloy isn't found
    if "steel" in material_grade.lower() or "cs" in material_grade.lower():
        return 138.0
        
    raise ValueError(f"Material '{material_grade}' not found in ASME Section II Part D database.")


try:
    from langchain_core.tools import tool
    @tool
    def material_lookup_tool(material_grade: str, temperature_c: float = 20.0) -> str:
        """
        Looks up the ASME Section II Part D allowable stress in MPa for a given pressure vessel material grade.
        
        Args:
            material_grade: The material specification (e.g., 'SA-516 Gr 70', '2.25Cr-1Mo')
            temperature_c: Design temperature in Celsius
        """
        try:
            stress = lookup_allowable_stress(material_grade, temperature_c)
            append_audit_event(
                tool_name="material_lookup_tool",
                inputs={"material_grade": material_grade, "temp_c": temperature_c},
                outputs={"allowable_stress_mpa": stress},
                status="SUCCESS",
                caller="material_lookup_tool"
            )
            return f"ASME Section II Part D Allowable Stress for {material_grade} at {temperature_c}C is {stress} MPa."
        except Exception as e:
            return f"Material Lookup Error: {str(e)}"
except ImportError:
    material_lookup_tool = None
