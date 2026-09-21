import math
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.inspection import Api579FfsInput, Api579FfsResult
from tools.audit_trail import AuditLedger

class Api579FfsTool:
    def __init__(self, use_audit_trail: bool = True):
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def evaluate_lta(self, inp: Api579FfsInput, caller_agent: str = "coder_agent") -> Api579FfsResult:
        # Pydantic boundary checks (gt=0) handle most validation automatically.
        
        # Cross-field logical validation
        if inp.t_min_lta > inp.t_actual_global:
            result = Api579FfsResult(status="ERROR", error="Minimum LTA thickness cannot be greater than global thickness.")
            return self._log_and_return(result, inp, caller_agent, "FAILED")

        Rt = inp.t_min_lta / inp.t_req
        if Rt < 0.20:
            result = Api579FfsResult(status="ERROR", error=f"Rt = {Rt:.3f} is below Level 1 screening limits (0.20). Level 2/3 required.")
            return self._log_and_return(result, inp, caller_agent, "FAILED")

        # Perform calculations
        diameter_mm = 2.0 * inp.inside_radius_mm
        sqrt_argument = diameter_mm * inp.t_req
        lambda_value = 1.285 * inp.flaw_length_mm / math.sqrt(sqrt_argument)
        Mt = math.sqrt(1.0 + (0.48 * lambda_value ** 2))
        denominator = 1.0 - ((1.0 - Rt) / Mt)
        
        if denominator <= 0:
            result = Api579FfsResult(status="ERROR", error="Invalid calculation parameters for RSF denominator.")
            return self._log_and_return(result, inp, caller_agent, "FAILED")

        rsf = Rt / denominator
        
        # The LLM passes the allowable RSF via the Pydantic schema
        is_acceptable = rsf >= inp.allowable_rsf

        if is_acceptable:
            action = "Acceptable for continued operation based on Level 1 RSF assessment."
        else:
            action = "Pressure derating or weld overlay required before turnaround."

        result = Api579FfsResult(
            status="SUCCESS",
            rsf=round(rsf, 3),
            allowable_rsf=inp.allowable_rsf,
            is_acceptable=is_acceptable,
            action=action
        )
        status_flag = "COMPLETED_SAFE" if is_acceptable else "CRITICAL_BREACH"
        return self._log_and_return(result, inp, caller_agent, status_flag)

    def _log_and_return(self, result: Api579FfsResult, inp: Api579FfsInput, caller_agent: str, status: str) -> Api579FfsResult:
        if self.use_audit_trail:
            self.ledger.append_event(
                event_type="ENGINEERING_CALCULATION",
                workflow_id="API_579_LTA_ASSESSMENT",
                tool_name="api_579_ffs_tool",
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
def run_ffs_assessment(
    t_actual_global: float,
    t_min_lta: float,
    t_req: float,
    flaw_length_mm: float,
    inside_radius_mm: float,
    allowable_rsf: float
) -> dict:
    """Runs API 579 Fitness-For-Service Assessment."""
    print(f"\n--- EXECUTING TOOL: run_ffs_assessment ---\n")
    logger.info(f"Executing tool: run_ffs_assessment")
    try:
        inp = Api579FfsInput(
            t_actual_global=t_actual_global,
            t_min_lta=t_min_lta,
            t_req=t_req,
            flaw_length_mm=flaw_length_mm,
            inside_radius_mm=inside_radius_mm,
            allowable_rsf=allowable_rsf
        )
        tool_instance = Api579FfsTool()
        return tool_instance.evaluate_lta(inp).model_dump()
    except Exception as e:
        logger.error(f"Error in run_ffs_assessment: {e}")
        return {"status": "error", "error": str(e)}

