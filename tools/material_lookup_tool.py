"""
tools/material_lookup_tool.py
ASME Section II Part D Metallurgy Database Tool
"""

MATERIAL_DB = {
    "2.25Cr-1Mo": {
        "material": "2.25Cr-1Mo (SA-387 Gr 22)",
        "temperatures": {
            350.0: {
                "allowable_stress_mpa": 138.0,
                "yield_strength_mpa": 310.0,
                "tensile_strength_mpa": 515.0
            }
        }
    },
    "SA-516 Gr 70": {
        "material": "SA-516 Gr 70",
        "temperatures": {
            350.0: {
                "allowable_stress_mpa": 120.0,
                "yield_strength_mpa": 260.0,
                "tensile_strength_mpa": 485.0
            }
        }
    },
    "SA-240 316L": {
        "material": "SA-240 316L",
        "temperatures": {
            350.0: {
                "allowable_stress_mpa": 100.0,
                "yield_strength_mpa": 170.0,
                "tensile_strength_mpa": 485.0
            }
        }
    }
}


def lookup_material(
    material_grade: str,
    temperature_c: float
) -> dict:
    """
    Look up material mechanical properties from offline ASME database.
    """
    if not isinstance(material_grade, str):
        return {
            "status": "ERROR",
            "error": "Material grade must be a string."
        }

    material_grade = material_grade.strip()

    if not material_grade:
        return {
            "status": "ERROR",
            "error": "Material grade cannot be empty."
        }

    if not isinstance(temperature_c, (int, float)):
        return {
            "status": "ERROR",
            "error": "Temperature must be a number."
        }

    if temperature_c != temperature_c:
        return {
            "status": "ERROR",
            "error": "Temperature cannot be NaN."
        }

    if material_grade not in MATERIAL_DB:
        return {
            "status": "ERROR",
            "error": f"Material '{material_grade}' not found in offline database."
        }

    material = MATERIAL_DB[material_grade]

    if temperature_c not in material["temperatures"]:
        return {
            "status": "ERROR",
            "error": (
                f"No verified data available for "
                f"{material_grade} at {temperature_c} °C."
            )
        }

    data = material["temperatures"][temperature_c]

    if data["allowable_stress_mpa"] <= 0:
        return {
            "status": "ERROR",
            "error": "Invalid allowable stress in database."
        }

    return {
        "status": "SUCCESS",
        "material": material["material"],
        "temperature_c": temperature_c,
        "allowable_stress_mpa": data["allowable_stress_mpa"],
        "yield_strength_mpa": data["yield_strength_mpa"],
        "tensile_strength_mpa": data["tensile_strength_mpa"]
    }


def lookup_allowable_stress(
    material_grade: str,
    temperature_c: float
) -> float:
    """
    Convenience function returning allowable stress (MPa) directly,
    or raising ValueError if material/temp is invalid.
    """
    result = lookup_material(material_grade, temperature_c)

    if result["status"] == "ERROR":
        raise ValueError(result["error"])

    return result["allowable_stress_mpa"]
