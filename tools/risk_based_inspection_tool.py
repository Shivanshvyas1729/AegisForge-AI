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


@tool
def calculate_rbi_score(inp: RbiIntervalInput) -> dict:
    """Calculates Risk Based Inspection (RBI) score and intervals."""
    print(f"\n--- EXECUTING TOOL: calculate_rbi_score ---\n")
    logger.info(f"Executing tool: calculate_rbi_score")
    try:
        rbi = RiskBasedInspectionTool()
        return rbi.calculate_rbi_interval(inp).model_dump()
    except Exception as e:
        logger.error(f"Error in calculate_rbi_score: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Test for RBI Tool
    logger.info("Testing calculate_rbi_score...")
    mock_input = RbiIntervalInput(
        remaining_life_years=10.0,
        design_pressure_mpa=1.5,
        fluid_toxicity="High",
        toxicity_factor=3,
        pressure_factor=2,
        life_factor=1
    )
    result = calculate_rbi_score.invoke({"inp": mock_input})
    logger.info(f"Result: {result}")
