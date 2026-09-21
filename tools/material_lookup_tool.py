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

    def _resolve_material_key(self, grade: str) -> str | None:
        """Fuzzy/alias resolver for engineering material specifications."""
        if grade in MATERIAL_DB:
            return grade
        g_clean = grade.lower().replace(" ", "").replace("-", "").replace(".", "")
        for k, v in MATERIAL_DB.items():
            k_clean = k.lower().replace(" ", "").replace("-", "").replace(".", "")
            full_name = v["material"].lower().replace(" ", "").replace("-", "").replace(".", "")
            if g_clean in k_clean or k_clean in g_clean or g_clean in full_name:
                return k
        # Common refinery aliases
        if any(x in g_clean for x in ["225cr", "sa387", "gr22", "chrome"]):
            return "2.25Cr-1Mo"
        elif any(x in g_clean for x in ["516", "sa516", "gr70", "carbon"]):
            return "SA-516 Gr 70"
        elif any(x in g_clean for x in ["316", "sa240", "stainless", "ss"]):
            return "SA-240 316L"
        return None

    def lookup_material(self, inp: MaterialLookupInput, caller_agent: str = "coder_agent") -> MaterialLookupResult:
        material_grade = inp.material_grade.strip()
        temperature_c = inp.temperature_c

        if not material_grade:
            result = MaterialLookupResult(status="ERROR", error="Material grade cannot be empty.")
            return self._log_and_return(result, inp, caller_agent, "FAILED")

        resolved_key = self._resolve_material_key(material_grade)
        if not resolved_key or resolved_key not in MATERIAL_DB:
            result = MaterialLookupResult(status="ERROR", error=f"Material '{material_grade}' not found in offline database.")
            return self._log_and_return(result, inp, caller_agent, "FAILED")

        material = MATERIAL_DB[resolved_key]
        temps = material["temperatures"]

        # If exact temperature is available use it, otherwise find the closest rated temperature
        if temperature_c in temps:
            rated_temp = temperature_c
        else:
            rated_temp = min(temps.keys(), key=lambda t: abs(t - temperature_c))

        data = temps[rated_temp]

        result = MaterialLookupResult(
            status="SUCCESS",
            material=material["material"],
            temperature_c=rated_temp,
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

