"""
Statutory Procurement & Vigilance Compliance Service
===================================================
Audits public sector procurements against CVC, GFR 2017, DoP, and PAC frameworks.
"""

from typing import Dict, Any, Optional
from tools.compliance_auditor import audit_cvc_compliance, ComplianceAuditor
from schemas.procurement import ProcurementRequest, AuditVerdict


class ComplianceService:
    """Service auditing public sector undertakings (PSUs) against statutory anti-corruption rules."""

    def audit_procurement(
        self,
        request_id: str,
        equipment_id: str,
        estimated_cost_lakhs: float,
        is_single_source: bool = True,
        has_pac: bool = False,
        is_emergency: bool = True,
        dop_authority: str = "General Manager",
        applicable_clause: str = "CVC Circular 02/02/2004 Clause 4.2 / GFR 2017 Rule 194 Emergency Exception",
    ) -> Dict[str, Any]:
        """
        Audits single-source, emergency procurements against Indian PSU statutory directives.
        """
        return audit_cvc_compliance.invoke({
            "request_id": request_id,
            "equipment_id": equipment_id,
            "estimated_cost_lakhs": float(estimated_cost_lakhs),
            "is_single_source": is_single_source,
            "has_pac": has_pac,
            "is_emergency": is_emergency,
            "dop_authority": dop_authority,
            "applicable_cvc_clause": applicable_clause
        })

    def get_supported_frameworks(self) -> list[str]:
        """
        Returns list of primary statutory procurement frameworks supported by AegisForge.
        """
        return [
            "CVC Circular 02/02/2004 Clause 4.2 (Single-Source Emergency Exception)",
            "GFR 2017 Rule 194 (Procurement from a Single Source)",
            "GFR 2017 Rule 166 (Proprietary Article Certificate - PAC)",
            "MRPL DoP Section 4.1 (Emergency Spares & Critical Shutdown Exemption)",
            "Custom Statutory Directive"
        ]
