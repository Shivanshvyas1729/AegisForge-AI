import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.inspection import MaterialLookupInput, MaterialLookupResult
from tools.audit_trail import AuditLedger

# Mock Database for the Demo. In a real system, the LLM could extract this via RAG 
# or query a real SQL database.
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

class MaterialLookupTool:
    def __init__(self, use_audit_trail: bool = True):
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def lookup_material(self, inp: MaterialLookupInput, caller_agent: str = "coder_agent") -> MaterialLookupResult:
        material_grade = inp.material_grade.strip()
        temperature_c = inp.temperature_c

        if not material_grade:
            result = MaterialLookupResult(status="ERROR", error="Material grade cannot be empty.")
            return self._log_and_return(result, inp, caller_agent, "FAILED")

        if material_grade not in MATERIAL_DB:
            result = MaterialLookupResult(status="ERROR", error=f"Material '{material_grade}' not found in offline database.")
            return self._log_and_return(result, inp, caller_agent, "FAILED")

        material = MATERIAL_DB[material_grade]

        if temperature_c not in material["temperatures"]:
            result = MaterialLookupResult(status="ERROR", error=f"No verified data available for {material_grade} at {temperature_c} °C.")
            return self._log_and_return(result, inp, caller_agent, "FAILED")

        data = material["temperatures"][temperature_c]

        result = MaterialLookupResult(
            status="SUCCESS",
            material=material["material"],
            temperature_c=temperature_c,
            allowable_stress_mpa=data["allowable_stress_mpa"],
            yield_strength_mpa=data["yield_strength_mpa"],
            tensile_strength_mpa=data["tensile_strength_mpa"]
        )
        return self._log_and_return(result, inp, caller_agent, "COMPLETED")

    def _log_and_return(self, result: MaterialLookupResult, inp: MaterialLookupInput, caller_agent: str, status: str) -> MaterialLookupResult:
        if self.use_audit_trail:
            self.ledger.append_event(
                event_type="DATA_EXTRACTION",
                workflow_id="MATERIAL_LOOKUP_AUDIT",
                tool_name="material_lookup_tool",
                caller=caller_agent,
                agent_version="1.0.0",
                tool_version="1.0.0",
                inputs=inp.model_dump(),
                outputs=result.model_dump(),
                status=status
            )
        return result

from langchain_core.tools import tool
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@tool
def lookup_material(
    material_grade: str,
    temperature_c: float
) -> dict:
    """Looks up allowable stress and material properties."""
    print(f"\n--- EXECUTING TOOL: lookup_material ---\n")
    logger.info(f"Executing tool: lookup_material")
    try:
        inp = MaterialLookupInput(
            material_grade=material_grade,
            temperature_c=temperature_c
        )
        tool_instance = MaterialLookupTool()
        return tool_instance.lookup_material(inp).model_dump()
    except Exception as e:
        logger.error(f"Error in lookup_material: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Test for Material Lookup
    logger.info("Testing lookup_material...")
    result = lookup_material.invoke({
        "material_grade": "SA-516 Grade 70",
        "temperature_c": 150.0
    })
    logger.info(f"Result: {result}")
