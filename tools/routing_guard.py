import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.routing import RoutingGuardVerdict
from tools.audit_trail import AuditLedger


class RoutingGuard:
    """
    Supervisor Dispatch Guard & 3-Way Human Approval Gate.

    Enforces human-in-the-loop governance whenever high-risk decisions
    or low-confidence parameters are detected by downstream agents.

    3-Way Gate:
        1. CONFIRM_UNEDITED   — Human engineer signs off on parameters as-is.
        2. CORRECT_AND_RERUN  — Engineer overrides inaccurate values and reruns.
        3. REJECT_AND_HALT    — Shuts down the pipeline immediately.
    """

    CONFIDENCE_THRESHOLD = 0.85

    def __init__(self, use_audit_trail: bool = True):
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def evaluate(self, extraction_output: dict, calculation_output: dict = None,
                 caller_agent: str = "supervisor_agent") -> RoutingGuardVerdict:
        """
        Evaluates whether automated dispatch should proceed or be blocked
        for human review.

        Args:
            extraction_output: Output from the Vision Agent's inspection extractor.
                Must contain 'status', 'confidence_score', 'requires_human_confirmation'.
            calculation_output: Optional output from the Coder Agent's ASME calculator.
                If it contains 'is_breach': True, the guard escalates to human review.
            caller_agent: The agent requesting the routing decision.

        Returns:
            RoutingGuardVerdict with routing decision.
        """
        # Rule 1: Check if Vision Agent flagged low confidence
        confidence = extraction_output.get("confidence_score", 0.0)
        requires_human = extraction_output.get("requires_human_confirmation", False)
        extraction_status = extraction_output.get("status", "UNKNOWN")

        if confidence < self.CONFIDENCE_THRESHOLD or requires_human:
            verdict = RoutingGuardVerdict(
                routing_verdict="DISPATCH_BLOCKED_AWAITING_HUMAN_CONFIRMATION",
                requires_human_confirmation=True,
                reason=f"OCR confidence {confidence:.2f} is below threshold {self.CONFIDENCE_THRESHOLD}. "
                       f"Extraction status: {extraction_status}.",
                risk_level="HIGH",
                suggested_action="CORRECT_AND_RERUN"
            )
            return self._log_and_return(verdict, extraction_output, calculation_output, caller_agent, "BLOCKED")

        # Rule 2: Check if ASME calculation detected a critical safety breach
        if calculation_output:
            is_breach = calculation_output.get("is_breach", False)
            status = calculation_output.get("status", "")

            if is_breach or "CRITICAL" in str(status).upper():
                verdict = RoutingGuardVerdict(
                    routing_verdict="DISPATCH_BLOCKED_CRITICAL_BREACH",
                    requires_human_confirmation=True,
                    reason=f"Critical safety breach detected in calculations. "
                           f"Status: {status}. Human engineer must review before proceeding.",
                    risk_level="CRITICAL",
                    suggested_action="CONFIRM_UNEDITED"
                )
                return self._log_and_return(verdict, extraction_output, calculation_output, caller_agent, "BLOCKED_BREACH")

        # Rule 3: Check if extraction found no parameters at all
        if extraction_status == "NO_PARAMETERS_FOUND":
            verdict = RoutingGuardVerdict(
                routing_verdict="DISPATCH_BLOCKED_NO_DATA",
                requires_human_confirmation=True,
                reason="OCR pipeline found no extractable parameters from the document.",
                risk_level="HIGH",
                suggested_action="REJECT_AND_HALT"
            )
            return self._log_and_return(verdict, extraction_output, calculation_output, caller_agent, "BLOCKED_NO_DATA")

        # All checks passed — safe to dispatch
        verdict = RoutingGuardVerdict(
            routing_verdict="DISPATCH_APPROVED",
            requires_human_confirmation=False,
            reason=f"All checks passed. Confidence: {confidence:.2f}. No safety breaches detected.",
            risk_level="LOW",
            suggested_action=None
        )
        return self._log_and_return(verdict, extraction_output, calculation_output, caller_agent, "APPROVED")

    def _log_and_return(self, verdict: RoutingGuardVerdict, extraction_output: dict,
                        calculation_output: dict, caller_agent: str, status: str) -> RoutingGuardVerdict:
        if self.use_audit_trail:
            self.ledger.append_event(
                event_type="ROUTING_DECISION",
                workflow_id="SUPERVISOR_DISPATCH_GUARD",
                tool_name="routing_guard",
                caller=caller_agent,
                agent_version="1.0.0",
                tool_version="1.0.0",
                inputs={
                    "extraction_output": extraction_output,
                    "calculation_output": calculation_output
                },
                outputs=verdict.model_dump(),
                status=status
            )
        return verdict

from langchain_core.tools import tool
from pydantic import BaseModel, Field
from typing import Optional
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class RoutingGuardInput(BaseModel):
    extraction_output: dict = Field(...)
    calculation_output: Optional[dict] = Field(None)
    compliance_output: Optional[dict] = Field(None)

@tool
def verify_routing_policy(inp: RoutingGuardInput) -> dict:
    """Verifies if the workflow can proceed based on extracted/calculated/compliance data."""
    print(f"\n--- EXECUTING TOOL: verify_routing_policy ---\n")
    logger.info(f"Executing tool: verify_routing_policy")
    try:
        guard = RoutingGuard()
        return guard.evaluate(inp.extraction_output, inp.calculation_output, inp.compliance_output).model_dump()
    except Exception as e:
        logger.error(f"Error in verify_routing_policy: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Test for Routing Guard
    logger.info("Testing verify_routing_policy...")
    mock_input = RoutingGuardInput(
        extraction_output={"status": "SUCCESS"},
        calculation_output={"status": "SAFE"},
        compliance_output=None
    )
    result = verify_routing_policy.invoke({"inp": mock_input})
    logger.info(f"Result: {result}")
