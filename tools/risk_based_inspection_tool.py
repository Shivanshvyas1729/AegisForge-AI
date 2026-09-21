import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.inspection import RbiIntervalInput, RbiIntervalResult
from tools.audit_trail import AuditLedger

class RiskBasedInspectionTool:
    def __init__(self, use_audit_trail: bool = True):
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def calculate_rbi_interval(self, inp: RbiIntervalInput, caller_agent: str = "coder_agent") -> RbiIntervalResult:
        # Pydantic boundary checks handle most validation automatically.
        
        # Calculate Risk Score purely based on LLM-provided factors
        risk_score = inp.toxicity_factor + inp.pressure_factor + inp.life_factor

        # Standard final categorization
        if risk_score >= 8:
            risk_category = "HIGH"
            recommended_interval_months = 6
            statutory_verdict = "ENGINEERING_REVIEW_REQUIRED"
        elif risk_score >= 6:
            risk_category = "MEDIUM_HIGH"
            recommended_interval_months = 12
            statutory_verdict = "ENHANCED_INSPECTION_REQUIRED"
        elif risk_score >= 4:
            risk_category = "MEDIUM"
            recommended_interval_months = 24
            statutory_verdict = "PERIODIC_INSPECTION_REQUIRED"
        else:
            risk_category = "LOW"
            recommended_interval_months = 36
            statutory_verdict = "ROUTINE_INSPECTION"

        result = RbiIntervalResult(
            status="SUCCESS",
            risk_category=risk_category,
            recommended_interval_months=recommended_interval_months,
            statutory_verdict=statutory_verdict
        )
        return self._log_and_return(result, inp, caller_agent, "COMPLETED_SAFE")

    def _log_and_return(self, result: RbiIntervalResult, inp: RbiIntervalInput, caller_agent: str, status: str) -> RbiIntervalResult:
        if self.use_audit_trail:
            self.ledger.append_event(
                event_type="ENGINEERING_CALCULATION",
                workflow_id="API_581_RBI_ASSESSMENT",
                tool_name="risk_based_inspection_tool",
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


RbiTool = RiskBasedInspectionTool

@tool
def calculate_rbi_score(
    equipment_id: str = "11-V-102",
    measured_thickness_mm: float = 138.2,
    design_pressure_mpa: float = 14.5,
    remaining_life_years: float = 5.0,
    fluid_toxicity: str = "High",
    toxicity_factor: float = 2.0,
    pressure_factor: float = 2.0,
    life_factor: float = 2.0
) -> dict:
    """Calculates Risk-Based Inspection (RBI) score and returns next inspection interval."""
    print(f"\n--- EXECUTING TOOL: calculate_rbi_score ---\n")
    logger.info(f"Executing tool: calculate_rbi_score")
    try:
        tf = max(1, min(3, int(round(toxicity_factor)))) if toxicity_factor is not None else 2
        pf = max(1, min(3, int(round(pressure_factor)))) if pressure_factor is not None else 2
        lf = max(1, min(3, int(round(life_factor)))) if life_factor is not None else 2
        dp = max(0.1, float(design_pressure_mpa)) if design_pressure_mpa is not None else 14.5
        
        rbi = RiskBasedInspectionTool()
        inp = RbiIntervalInput(
            equipment_id=equipment_id or "11-V-102",
            measured_thickness_mm=measured_thickness_mm if measured_thickness_mm is not None else 138.2,
            design_pressure_mpa=dp,
            remaining_life_years=remaining_life_years if remaining_life_years is not None else 5.0,
            fluid_toxicity=fluid_toxicity or "High",
            toxicity_factor=tf,
            pressure_factor=pf,
            life_factor=lf
        )
        return rbi.calculate_rbi_interval(inp).model_dump()
    except Exception as e:
        logger.error(f"Error in calculate_rbi_score: {e}")
        return {"status": "error", "error": str(e)}

