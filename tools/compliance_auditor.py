import sys
import os

# Ensure the root workspace is in the python path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from typing import List, Callable
from schemas.procurement import ProcurementRequest, AuditVerdict
from tools.audit_trail import AuditLedger

# ---------------------------------------------------------
# Isolated Rule Functions (Scalable Pattern)
# ---------------------------------------------------------

def rule_check_single_source(request: ProcurementRequest) -> str | None:
    """Ensures single-source procurements have valid statutory exceptions."""
    if request.is_single_source:
        if not request.has_pac and not request.is_emergency:
            return "CRITICAL VIOLATION: Single-source procurement attempted without an Emergency justification or valid PAC."
        if "cvc" not in request.applicable_cvc_clause.lower() and "exception" not in request.applicable_cvc_clause.lower():
            return "CRITICAL VIOLATION: Invalid or missing CVC sanction clause provided by LLM for single-source procurement."
    return None

def rule_check_vendor_blacklist(request: ProcurementRequest) -> str | None:
    """Ensures we do not do business with blacklisted entities."""
    if request.vendor_is_blacklisted:
        return "CRITICAL VIOLATION: Vendor is on the active CVC Blacklist."
    return None

# ---------------------------------------------------------
# The Deterministic Rules Engine
# ---------------------------------------------------------

class ComplianceAuditor:
    def __init__(self, use_audit_trail: bool = True):
        # Register all active statutory rules here
        self.rules: List[Callable[[ProcurementRequest], str | None]] = [
            rule_check_single_source,
            rule_check_vendor_blacklist
        ]
        
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            # Initialize the cryptographic ledger for financial compliance logging
            self.ledger = AuditLedger()

    def evaluate(self, request: ProcurementRequest) -> AuditVerdict:
        violations = []
        
        # Execute all rules cleanly
        for rule in self.rules:
            violation = rule(request)
            if violation:
                violations.append(violation)
             
        is_compliant = len(violations) == 0
        
        verdict = AuditVerdict(
            is_compliant=is_compliant,
            competent_financial_authority=request.required_financial_authority if is_compliant else "NONE",
            sanction_clause=request.applicable_cvc_clause if is_compliant else "NONE",
            violations=violations
        )
        
        # Cryptographically log the compliance decision
        if self.use_audit_trail:
            status = "APPROVED" if is_compliant else "BLOCKED_BY_COMPLIANCE"
            self.ledger.append_event(
                event_type="COMPLIANCE_CHECK",
                workflow_id="PROCUREMENT_AUDIT",
                tool_name="compliance_auditor",
                caller="reasoning_agent",
                agent_version="1.0.0",
                tool_version="1.5.0",
                inputs=request.model_dump(),
                outputs=verdict.model_dump(),
                status=status
            )
            
        return verdict


from langchain_core.tools import tool
from schemas.procurement import ProcurementRequest
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@tool
def audit_cvc_compliance(
    request_id: str,
    amount_inr: float,
    is_single_source: bool,
    has_pac: bool,
    is_emergency: bool,
    applicable_cvc_clause: str,
    dop_authority: str
) -> dict:
    """Audits compliance with CVC rules based on procurement request."""
    print(f"\n--- EXECUTING TOOL: audit_cvc_compliance ---\n")
    logger.info(f"Executing tool: audit_cvc_compliance")
    try:
        request = ProcurementRequest(
            request_id=request_id,
            amount_inr=amount_inr,
            is_single_source=is_single_source,
            has_pac=has_pac,
            is_emergency=is_emergency,
            applicable_cvc_clause=applicable_cvc_clause,
            dop_authority=dop_authority
        )
        auditor = ComplianceAuditor()
        return auditor.evaluate(request).model_dump()
    except Exception as e:
        logger.error(f"Error in audit_cvc_compliance: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Test for Compliance Auditor
    logger.info("Testing audit_cvc_compliance...")
    result = audit_cvc_compliance.invoke({
        "request_id": "REQ-123",
        "amount_inr": 500000.0,
        "is_single_source": True,
        "has_pac": False,
        "is_emergency": True,
        "applicable_cvc_clause": "CVC Circular 02/02/2004 Emergency Exception",
        "dop_authority": "Director"
    })
    logger.info(f"Result: {result}")
