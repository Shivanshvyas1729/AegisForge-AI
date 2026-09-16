"""
tools/compliance_auditor.py
Central Vigilance Commission (CVC) & PSU Delegation of Powers (DoP) Statutory Compliance Engine.
Audits emergency procurement, sole-source justifications, and financial sanction thresholds
against formal circulars and schedules, defaulting to fail-safe strictness.
"""

import sys
import time
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.audit_trail import append_audit_event

# Formal Statutory Regulation Registry with Versioning & Metadata
REGULATION_REGISTRY = {
    "CVC_CIRCULAR_02_2004": {
        "reference": "CVC Office Order No. 02/02/2004 (Ref: 98/ORD/1)",
        "effective_date": "2004-02-02",
        "title": "Guidelines on Tendering in PSUs - Restrictions on Negotiations & Single Source Awards",
        "mandate": (
            "Single-source tendering is an exception to the rule of open competitive bidding and is permissible "
            "strictly under genuine operational emergencies or for proprietary items with valid technical PAC."
        ),
    },
    "IOCL_DOP_CLAUSE_4_2": {
        "reference": "IOCL Delegation of Powers (DoP) 2023 - Schedule Item 4.2",
        "effective_date": "2023-04-01",
        "title": "Procurement on Single Tender / Proprietary Article Certificate (PAC) Basis",
        "mandate": (
            "Requires mandatory technical justification by user department confirming that no acceptable "
            "substitute exists and delays would jeopardize refinery life-safety or statutory operations."
        ),
    },
    "IOCL_DOP_CLAUSE_2_1": {
        "reference": "IOCL Delegation of Powers (DoP) 2023 - Financial Competence Levels",
        "thresholds": [
            {"max_lakhs": 25.0, "authority": "Chief General Manager (CGM) / CGM(TS)"},
            {"max_lakhs": 50.0, "authority": "Executive Director (ED) / Head of Refinery"},
            {"max_lakhs": 100.0, "authority": "Director (Refineries)"},
            {"max_lakhs": float("inf"), "authority": "Chairman / Board of Directors"},
        ],
    },
}


# Provenance Metadata for Air-Gapped Sovereign Operation
PAC_REGISTRY_METADATA = {
    "provenance_type": "OFFLINE_LOCAL_SNAPSHOT_CACHE",
    "source_erp_system": "IOCL SAP ERP Materials Management / Plant Maintenance (MM/PM)",
    "snapshot_sync_timestamp_utc": "2026-09-16T00:00:00Z",
    "reconciliation_policy": (
        "In an air-gapped sovereign deployment, plant maintenance data is synchronized as an authenticated "
        "local snapshot. Automated evaluation cross-references against this local cache; final statutory physical "
        "ratification against live SAP records remains the mandatory duty of the Chief Approving Authority."
    ),
}

# Authoritative Local Snapshot Registry of Officially Issued & Ratified PAC Certificates
VERIFIED_PAC_REGISTRY = {
    "PAC-2026-OEM-V102": {
        "equipment_id": "11-V-102",
        "oem_vendor": "Larsen & Toubro Heavy Engineering",
        "valid_until": "2027-03-31",
        "scope": "Emergency weld overlay and metallurgical cladding restoration for 2.25Cr-1Mo shell.",
        "status": "VALID_ACTIVE",
    },
    "PAC-2025-LNT-HYDROCRACKER-001": {
        "equipment_id": "12-C-101",
        "oem_vendor": "Larsen & Toubro Heavy Engineering",
        "valid_until": "2026-12-31",
        "scope": "Hydrocracker column tray proprietary replacement.",
        "status": "VALID_ACTIVE",
    },
}


def audit_procurement_compliance(
    equipment_id: str,
    estimated_cost_lakhs: float,
    is_emergency: bool = False,
    is_single_source: bool = False,
    has_pac: bool = False,
    pac_certificate_ref: Optional[str] = None,
    emergency_justification_ref: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Evaluates procurement request against CVC Circular 02/02/2004 and IOCL DoP Schedule 4.2.
    Defaults to strictest non-permissive stance (all flags False).
    Enforces Evidence-Level Verification: cross-checks cited PAC identifiers against
    the authoritative VERIFIED_PAC_REGISTRY to reject hallucinated or unverified citations.
    """
    if estimated_cost_lakhs <= 0:
        raise ValueError(f"Estimated cost must be positive, got {estimated_cost_lakhs} Lakhs.")

    # 1. Determine Competent Financial Approval Authority
    approving_authority = "Chairman / Board of Directors"
    for tier in REGULATION_REGISTRY["IOCL_DOP_CLAUSE_2_1"]["thresholds"]:
        if estimated_cost_lakhs <= tier["max_lakhs"]:
            approving_authority = tier["authority"]
            break

    # 2. Verify Caller Evidence References against Authoritative Registry
    violations = []
    justifications = []

    if has_pac:
        if not pac_certificate_ref:
            violations.append(
                "VIOLATION: Proprietary Article Certificate (PAC) claimed, but no valid 'pac_certificate_ref' identifier was cited."
            )
        elif pac_certificate_ref not in VERIFIED_PAC_REGISTRY:
            violations.append(
                f"VIOLATION: Cited PAC identifier '{pac_certificate_ref}' was NOT found in the verified PSU PAC Certificate Registry (unverified citation rejected)."
            )
        else:
            pac_entry = VERIFIED_PAC_REGISTRY[pac_certificate_ref]
            if pac_entry.get("status") != "VALID_ACTIVE":
                violations.append(
                    f"VIOLATION: Cited PAC '{pac_certificate_ref}' is marked as {pac_entry.get('status')} and is not active."
                )

    if is_emergency and not emergency_justification_ref:
        violations.append(
            "VIOLATION: Operational emergency claimed, but no valid 'emergency_justification_ref' incident code was cited."
        )

    if is_single_source:
        if not is_emergency and not has_pac:
            violations.append(
                "VIOLATION: Single-source procurement without documented operational emergency or PAC certificate "
                "is strictly prohibited under CVC Circular 02/02/2004."
            )
        elif is_emergency and not has_pac:
            justifications.append(
                f"Emergency Justification ({emergency_justification_ref or 'UNVERIFIED'}): Operational emergency invoked "
                "under CVC Circular 02/02/2004 to prevent imminent production shutdown."
            )
            violations.append(
                "NOTE: Proprietary Article Certificate (PAC) is missing; requires post-facto technical ratification."
            )
        elif not is_emergency and has_pac:
            justifications.append(
                f"PAC Justification ({pac_certificate_ref or 'UNVERIFIED'}): Single-source procurement justified "
                "under IOCL DoP Schedule Item 4.2 with formal OEM PAC certificate."
            )
        else:
            # Both emergency and PAC
            justifications.append(
                f"Dual Statutory Justification: Operational emergency [{emergency_justification_ref}] under CVC Circular 02/02/2004 "
                f"substantiated by Proprietary Article Certificate [{pac_certificate_ref}] under IOCL DoP Schedule Item 4.2."
            )

    is_compliant = len([v for v in violations if v.startswith("VIOLATION")]) == 0
    verdict = "COMPLIANT_STATUTORILY_JUSTIFIED" if is_compliant else "NON_COMPLIANT_CVC_VIOLATION"

    return {
        "equipment_id": equipment_id,
        "estimated_cost_lakhs": estimated_cost_lakhs,
        "is_compliant": is_compliant,
        "compliance_verdict": verdict,
        "competent_approving_authority": approving_authority,
        "pac_certificate_ref": pac_certificate_ref,
        "emergency_justification_ref": emergency_justification_ref,
        "registry_provenance": PAC_REGISTRY_METADATA["provenance_type"],
        "statutory_clauses_cited": [
            REGULATION_REGISTRY["CVC_CIRCULAR_02_2004"]["reference"],
            REGULATION_REGISTRY["IOCL_DOP_CLAUSE_4_2"]["reference"],
        ],
        "justifications": justifications,
        "violations": violations,
    }


try:
    from langchain_core.tools import tool

    @tool
    def cvc_audit_tool(
        equipment_id: str,
        estimated_cost_lakhs: float,
        is_emergency: bool = False,
        is_single_source: bool = False,
        has_pac: bool = False,
        pac_certificate_ref: Optional[str] = None,
        emergency_justification_ref: Optional[str] = None,
    ) -> str:
        """
        Audits single-source or emergency procurement compliance against CVC Circular 02/02/2004
        and IOCL Delegation of Powers (DoP) Schedule 4.2.
        All compliance flags default to False (strictest/least-favorable stance).
        Requires explicit document or incident reference IDs when compliance flags are asserted.
        
        Args:
            equipment_id: Equipment tag identifier (e.g. '11-V-102') [REQUIRED]
            estimated_cost_lakhs: Estimated cost in Indian Rupees (Lakhs) [REQUIRED, > 0]
            is_emergency: Whether a life-safety / imminent shutdown emergency exists (default False)
            is_single_source: Whether procurement is single-tender / sole-source (default False)
            has_pac: Whether a valid Proprietary Article Certificate is on record (default False)
            pac_certificate_ref: Reference identifier for OEM PAC certificate (e.g. 'PAC/2026/IOCL-V102')
            emergency_justification_ref: Incident or risk ticket reference (e.g. 'INC-2026-CRIT-004')
        """
        start_time = time.time()
        inputs = {
            "equipment_id": equipment_id,
            "estimated_cost_lakhs": estimated_cost_lakhs,
            "is_emergency": is_emergency,
            "is_single_source": is_single_source,
            "has_pac": has_pac,
            "pac_certificate_ref": pac_certificate_ref,
            "emergency_justification_ref": emergency_justification_ref,
        }

        try:
            res = audit_procurement_compliance(
                equipment_id=equipment_id,
                estimated_cost_lakhs=estimated_cost_lakhs,
                is_emergency=is_emergency,
                is_single_source=is_single_source,
                has_pac=has_pac,
                pac_certificate_ref=pac_certificate_ref,
                emergency_justification_ref=emergency_justification_ref,
            )
            duration_ms = (time.time() - start_time) * 1000

            append_audit_event(
                tool_name="cvc_audit_tool",
                inputs=inputs,
                outputs=res,
                status="SUCCESS",
                duration_ms=duration_ms,
                caller="cvc_audit_tool"
            )

            status_icon = "PASS" if res["is_compliant"] else "ALERT: AUDIT OBJECTION"
            lines = [
                f"Statutory Procurement & CVC Audit for {equipment_id} (Rs. {estimated_cost_lakhs} Lakhs):",
                f"- Audit Status: {status_icon} ({res['compliance_verdict']})",
                f"- Competent Approval Authority: {res['competent_approving_authority']}",
                f"- Regulations Applied: {', '.join(res['statutory_clauses_cited'])}",
            ]

            if res["justifications"]:
                lines.append("- Justification Clauses:")
                for j in res["justifications"]:
                    lines.append(f"  * {j}")

            if res["violations"]:
                lines.append("- Compliance Warnings / Objections:")
                for v in res["violations"]:
                    lines.append(f"  * {v}")

            return "\n".join(lines)

        except Exception as e:
            duration_ms = (time.time() - start_time) * 1000
            append_audit_event(
                tool_name="cvc_audit_tool",
                inputs=inputs,
                outputs={"error": str(e)},
                status="FAILURE",
                duration_ms=duration_ms,
                caller="cvc_audit_tool"
            )
            return f"CVC Audit Error: {str(e)}"

except ImportError:
    cvc_audit_tool = None
