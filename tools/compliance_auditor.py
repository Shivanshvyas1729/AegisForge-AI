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
    """Ensures single-source procurements have valid statutory exceptions under CVC, GFR, PAC, or DoP rules."""
    if request.is_single_source:
        if not request.has_pac and not request.is_emergency:
            return "CRITICAL VIOLATION: Single-source procurement attempted without an Emergency justification or valid PAC."
        clause_lower = request.applicable_cvc_clause.lower()
        valid_frameworks = [
            "cvc", "gfr", "pac", "emergency", "dpe", "oisd", "dop",
            "circular", "rule", "section", "clause", "justification", "exception", "manual", "order"
        ]
        if not any(fw in clause_lower for fw in valid_frameworks):
            return "CRITICAL VIOLATION: Procurement does not cite a valid statutory framework (e.g. CVC, GFR 2017, PAC, or DoP emergency exception)."
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


from typing import Any, Optional, Union
from pydantic import BaseModel, ConfigDict, Field


def _to_bool(val: Any, default: bool = False) -> bool:
    if val is None:
        return default
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    if isinstance(val, str):
        return val.strip().lower() in ("true", "1", "yes", "y", "t")
    return bool(val)


class CvcComplianceInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    request_id: str = Field(default="REQ-001", description="Procurement request identifier")
    equipment_id: str = Field(default="PROCUREMENT-ITEM", description="Equipment tag or identifier")
    amount_inr: float = Field(default=0.0, description="Total amount in Indian Rupees")
    estimated_cost_lakhs: float = Field(default=0.0, description="Estimated cost in Lakhs")
    is_single_source: Union[bool, str] = Field(default=True, description="Whether procurement is single-source")
    has_pac: Union[bool, str] = Field(default=False, description="Whether Proprietary Article Certificate is held")
    is_emergency: Union[bool, str] = Field(default=False, description="Whether this is an emergency life-safety procurement")
    vendor_is_blacklisted: Union[bool, str] = Field(default=False, description="Whether vendor is blacklisted")
    applicable_cvc_clause: str = Field(
        default="Statutory Exception under CVC / GFR / DoP Guidelines",
        description="Applicable circular or statutory clause"
    )
    dop_authority: str = Field(default="Director (Refineries)", description="Delegation of Power sanction authority")
    required_financial_authority: str = Field(default="Director (Refineries)", description="Competent Financial Authority")
    kwargs: Optional[Any] = Field(default=None, description="Optional extra arguments dictionary")


@tool(args_schema=CvcComplianceInput)
def audit_cvc_compliance(
    request_id: str = "REQ-001",
    equipment_id: str = "PROCUREMENT-ITEM",
    amount_inr: float = 0.0,
    estimated_cost_lakhs: float = 0.0,
    is_single_source: Union[bool, str] = True,
    has_pac: Union[bool, str] = False,
    is_emergency: Union[bool, str] = False,
    vendor_is_blacklisted: Union[bool, str] = False,
    applicable_cvc_clause: str = "Statutory Exception under CVC / GFR / DoP Guidelines",
    dop_authority: str = "Director (Refineries)",
    required_financial_authority: str = "Director (Refineries)",
    **kwargs: Any
) -> dict:
    """Audits compliance with PSU statutory procurement rules (CVC, GFR 2017, DoP, PAC)."""
    print(f"\n--- EXECUTING TOOL: audit_cvc_compliance ---\n")
    logger.info(f"Executing tool: audit_cvc_compliance (Equipment: {equipment_id})")
    try:
        # Resolve dynamic aliases
        eq_id = equipment_id or kwargs.get("tag") or request_id or "PROCUREMENT-ITEM"
        cost_lakhs = (
            estimated_cost_lakhs
            or kwargs.get("cost_lakhs")
            or kwargs.get("estimated_cost")
            or (amount_inr / 100000.0 if amount_inr > 0 else 0.0)
            or (float(kwargs.get("amount", 0)) / 100000.0 if kwargs.get("amount") else 0.0)
        )
        auth   = kwargs.get("authority") or required_financial_authority or dop_authority or "Competent Financial Authority"
        clause = kwargs.get("clause") or kwargs.get("circular") or applicable_cvc_clause or "Statutory Exception"

        request = ProcurementRequest(
            equipment_id=eq_id,
            estimated_cost_lakhs=float(cost_lakhs),
            is_single_source=_to_bool(is_single_source, default=True),
            has_pac=_to_bool(has_pac, default=False),
            is_emergency=_to_bool(is_emergency, default=False),
            vendor_is_blacklisted=_to_bool(vendor_is_blacklisted, default=False),
            applicable_cvc_clause=clause,
            required_financial_authority=auth
        )
        auditor = ComplianceAuditor()
        res = auditor.evaluate(request).model_dump()
        res["compliance_status"] = "COMPLIANT" if res.get("is_compliant") else "NON_COMPLIANT"
        res["status"] = res["compliance_status"]
        return res
    except Exception as e:
        logger.error(f"Error in audit_cvc_compliance: {e}")
        return {"status": "error", "compliance_status": "ERROR", "error": str(e)}


# =============================================================================
# Sovereign Mining Domain Policy & Statutory Compliance Auditor
# =============================================================================

from schemas.mining import MiningAuditInput, MiningAuditVerdict

class MiningPolicyAuditInput(BaseModel):
    model_config = ConfigDict(extra="allow")

    mine_id: str = Field(default="MINE-001", description="Colliery / Mine ID or block name")
    subsidiary: str = Field(default="CMPDI", description="CIL Subsidiary (CMPDI, ECL, BCCL, CCL, WCL, SECL, MCL, NCL)")
    planned_production_mt: float = Field(default=5.0, description="Annual target production in Million Tonnes (MT)")
    actual_production_mt: float = Field(default=4.2, description="Actual achieved production in Million Tonnes (MT)")
    calculated_stripping_ratio: float = Field(default=3.2, description="Actual calculated stripping ratio (BCM/tonne)")
    approved_stripping_ratio: float = Field(default=2.8, description="Approved Project Report benchmark stripping ratio")
    statutory_reserves_mt: Optional[float] = Field(default=None, description="Certified geological reserve in MT")
    cmr_regulation_clause: str = Field(default="CMR 2017 Reg 104", description="Applicable Coal Mines Regulation clause")


@tool(args_schema=MiningPolicyAuditInput)
def audit_mining_compliance(
    mine_id: str = "MINE-001",
    subsidiary: str = "CMPDI",
    planned_production_mt: float = 5.0,
    actual_production_mt: float = 4.2,
    calculated_stripping_ratio: float = 3.2,
    approved_stripping_ratio: float = 2.8,
    statutory_reserves_mt: Optional[float] = None,
    cmr_regulation_clause: str = "CMR 2017 Reg 104",
    **kwargs: Any
) -> dict:
    """
    Audits coal mine operational performance against statutory mandates:
    - Production Shortfall against Annual Action Plan (AAP) targets (> 10% requires DGMS/MoC explanation)
    - Stripping Ratio deviation from Approved Project Report (> 20% violates CMR 2017 Reg 104 bench schedule)
    - Statutory Geological Reserve thresholds (< 1.0 MT falls below commercial viability)
    """
    logger.info(f"Executing tool: audit_mining_compliance (Mine: {mine_id}, Sub: {subsidiary})")
    violations = []
    remedials = []

    # 1. Production shortfall calculation
    shortfall_mt = max(planned_production_mt - actual_production_mt, 0.0)
    shortfall_pct = round((shortfall_mt / planned_production_mt) * 100, 2) if planned_production_mt > 0 else 0.0
    if shortfall_pct > 10.0:
        violations.append(
            f"Production Shortfall Violation: Achieved {actual_production_mt:.2f} MT vs Target {planned_production_mt:.2f} MT "
            f"({shortfall_pct:.1f}% deficit exceeds Ministry 10% threshold)."
        )
        remedials.append("Mobilize high-capacity HEMM dragline/shovel fleet and deploy additional working faces.")

    # 2. Stripping ratio deviation calculation
    sr_dev_pct = 0.0
    if approved_stripping_ratio > 0:
        sr_dev_pct = round(((calculated_stripping_ratio - approved_stripping_ratio) / approved_stripping_ratio) * 100, 2)
        if sr_dev_pct > 20.0:
            violations.append(
                f"Stripping Ratio Non-Compliance: Operating at {calculated_stripping_ratio:.2f} BCM/te vs Approved PR "
                f"{approved_stripping_ratio:.2f} BCM/te ({sr_dev_pct:+.1f}% deviation exceeds CMR 2017 Reg 104 bench limits)."
            )
            remedials.append("Realign overburden advance stripping schedule to restore bench stability and safety margins.")

    # 3. Statutory reserve threshold
    if statutory_reserves_mt is not None:
        if statutory_reserves_mt < 1.0:
            violations.append(
                f"Statutory Reserve Deficit: Block reserve of {statutory_reserves_mt:.2f} MT is below the 1.0 MT "
                "commercial viability threshold under CMPDI UNFC-111 reporting norms."
            )
            remedials.append("Conduct infill exploratory drilling (<= 400m grid spacing) to upgrade Inferred to Proved reserves.")

    is_compliant = len(violations) == 0

    verdict = MiningAuditVerdict(
        is_compliant=is_compliant,
        competent_statutory_authority="Director General of Mines Safety (DGMS) / Ministry of Coal",
        production_shortfall_percentage=shortfall_pct,
        stripping_ratio_deviation_percentage=sr_dev_pct,
        sanction_clause=cmr_regulation_clause,
        violations=violations,
        remedial_recommendations=remedials
    )

    ledger = AuditLedger()
    ledger.append_event(
        event_type="COMPLIANCE_CHECK",
        workflow_id="MINING_STATUTORY_AUDIT",
        tool_name="compliance_auditor",
        caller="reasoning_agent",
        agent_version="2.0.0",
        tool_version="2.0.0",
        inputs={
            "mine_id": mine_id, "subsidiary": subsidiary,
            "planned_production_mt": planned_production_mt, "actual_production_mt": actual_production_mt,
            "calculated_stripping_ratio": calculated_stripping_ratio
        },
        outputs=verdict.model_dump(),
        status="APPROVED_STATUTORY_COMPLIANT" if is_compliant else "FLAGGED_REGULATORY_VIOLATION"
    )

    res = verdict.model_dump()
    res["compliance_status"] = "STATUTORILY_COMPLIANT" if is_compliant else "FLAGGED_VIOLATION"
    res["status"] = res["compliance_status"]
    return res



