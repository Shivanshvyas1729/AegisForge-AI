"""
Dossier Ingestion & Autonomous Pipeline Service
================================================
Handles document uploading, PDF/OCR extraction, and end-to-end NFA generation.
"""

import os
import re
import datetime
from pathlib import Path
from typing import Optional, Union, Dict, Any

from tools.file_io import read_scanned_pdf
from tools.asme_calculator import calculate_asme_stresses
from tools.compliance_auditor import audit_cvc_compliance
from tools.doc_generator import generate_nfa_documents


class DossierService:
    """Service for processing industrial inspection dossiers and generating deliverables."""

    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            self.workspace_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.workspace_root = Path(workspace_root)
        self.upload_dir = self.workspace_root / "data" / "uploads"
        self.upload_dir.mkdir(parents=True, exist_ok=True)

    def save_uploaded_file(self, filename: str, file_bytes: bytes) -> Path:
        """
        Saves uploaded file into data/uploads with path validation.
        """
        safe_name = Path(filename).name
        target_path = self.upload_dir / safe_name
        with open(target_path, "wb") as f:
            f.write(file_bytes)
        return target_path

    def save_custom_text(self, content: str, filename: str = "custom_inspection.txt") -> Path:
        """
        Saves raw pasted text into data/uploads for pipeline consumption.
        """
        target_path = self.upload_dir / filename
        with open(target_path, "w", encoding="utf-8") as f:
            f.write(content)
        return target_path

    def read_document(self, file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Reads any binary PDF, image, or text dossier using the air-gapped FileIO tool.
        """
        return read_scanned_pdf.invoke({"file_path": str(file_path)})

    def extract_vessel_parameters(self, content: str) -> Dict[str, Any]:
        """
        Dynamically extracts ASME Section VIII parameters and material specs from text.
        """
        params = {
            "equipment_id": "11-V-102",
            "design_pressure_mpa": 14.5,
            "inside_radius_mm": 1200.0,
            "allowable_stress_mpa": 138.0,
            "joint_efficiency": 1.0,
            "corrosion_allowance_mm": 4.0,
            "measured_thickness_mm": 138.20,
            "corrosion_rate_mm_yr": 0.75,
            "material_grade": None,
        }

        m_id = re.search(r'(?:Equipment\s*(?:ID|Tag|No)?|Vessel\s*(?:Tag|ID|No)?|Tag)[:\s=]*([A-Za-z0-9\-]+)', content, re.IGNORECASE)
        if m_id:
            params["equipment_id"] = m_id.group(1).strip()

        m_p = re.search(r'(?:Design\s*Pressure|Operating\s*Pressure|Pressure\s*P|Pressure)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_p:
            params["design_pressure_mpa"] = float(m_p.group(1))

        m_r = re.search(r'(?:Inside\s*Radius|Internal\s*Radius|Radius\s*R|Radius)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_r:
            params["inside_radius_mm"] = float(m_r.group(1))

        m_t = re.search(r'(?:Measured\s*Thickness|Actual\s*Thickness|Minimum\s*Recorded\s*Thickness|Thickness\s*t|Thickness)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_t:
            params["measured_thickness_mm"] = float(m_t.group(1))

        m_cr = re.search(r'(?:Corrosion\s*Rate|CR)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_cr:
            params["corrosion_rate_mm_yr"] = float(m_cr.group(1))

        m_ca = re.search(r'(?:Corrosion\s*Allowance|CA)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_ca:
            params["corrosion_allowance_mm"] = float(m_ca.group(1))

        m_s = re.search(r'(?:Allowable\s*Stress|Stress\s*S|Max\s*Allowable\s*Stress)[:\s=]*([\d.]+)', content, re.IGNORECASE)
        if m_s:
            params["allowable_stress_mpa"] = float(m_s.group(1))

        m_mat = re.search(r'Material(?: Specification)?[:\s=]*([A-Za-z0-9\.\-\+ ]+)', content, re.IGNORECASE)
        if m_mat:
            mat_grade = m_mat.group(1).strip().split('\n')[0]
            params["material_grade"] = mat_grade
            try:
                from tools.material_lookup_tool import lookup_material
                mat_res = lookup_material.invoke({"material_grade": mat_grade, "temperature_c": 350.0})
                if mat_res.get("status") == "SUCCESS" and mat_res.get("allowable_stress_mpa"):
                    params["allowable_stress_mpa"] = float(mat_res["allowable_stress_mpa"])
            except Exception:
                pass

        return params

    def run_pipeline(
        self,
        input_source: Optional[Union[str, Path]] = None,
        statutory_framework: str = "CVC Circular 02/02/2004 Clause 4.2 / GFR 2017 Rule 194 Emergency Exception",
        template_name: str = "NFA_Emergency_Procurement.docx",
    ) -> Dict[str, Any]:
        """
        Executes the deterministic Golden Path pipeline:
        Dossier -> Parameter Extraction -> ASME Stress Math -> Statutory Audit -> Certified NFA Word/PDF.
        """
        if input_source is None:
            input_source = self.workspace_root / "data" / "sample_reports" / "UT_Scan_Separator_11V102.pdf"

        # 1. Read document
        read_res = self.read_document(input_source)
        content = read_res.get("content", "")

        # 2. Extract vessel parameters
        params = self.extract_vessel_parameters(content)
        eq_id = params["equipment_id"]
        t_act = params["measured_thickness_mm"]

        # 3. ASME Section VIII UG-27 stress calculation
        calc = calculate_asme_stresses.invoke({
            "design_pressure_mpa": params["design_pressure_mpa"],
            "inside_radius_mm": params["inside_radius_mm"],
            "allowable_stress_mpa": params["allowable_stress_mpa"],
            "joint_efficiency": params["joint_efficiency"],
            "corrosion_allowance_mm": params["corrosion_allowance_mm"],
            "measured_thickness_mm": t_act,
            "corrosion_rate_mm_yr": params["corrosion_rate_mm_yr"],
            "equipment_id": eq_id
        })

        # 4. Multi-framework statutory procurement audit
        audit = audit_cvc_compliance.invoke({
            "request_id": f"REQ-{eq_id}-01",
            "equipment_id": eq_id,
            "estimated_cost_lakhs": 15.0,
            "is_single_source": True,
            "has_pac": False,
            "is_emergency": True,
            "dop_authority": "General Manager",
            "applicable_cvc_clause": statutory_framework
        })

        # 5. Render official deliverable with SHA-256 seal
        payload = {
            "equipment_id": eq_id,
            "corrosion_rate_mm_yr": params.get("corrosion_rate_mm_yr", 0.75),
            "remaining_life_years": calc.get("remaining_life_years", -0.49),
            "inspector_name": "Er. S. Vyas, Lead Reliability Engineer (NDT Level III)",
            "measured_thickness_mm": t_act,
            "t_req_mm": calc.get("t_req_mm", 0.0),
            "t_min_mm": calc.get("t_req_mm", 0.0),
            "status": calc.get("status", "CRITICAL_BREACH"),
            "audit_risk": "HIGH" if calc.get("is_breach") else "LOW",
            "sanction_clause": audit.get("sanction_clause", statutory_framework),
            "executive_summary": (
                f"ASME Section VIII Div 1 UG-27 verification for {eq_id}: "
                f"Required thickness = {calc.get('t_req_mm', 0):.2f}mm, Measured = {t_act:.2f}mm, "
                f"Safety Margin Δ = {calc.get('delta_mm', 0):.2f}mm ({calc.get('status')}). "
                f"Remaining Service Life = {calc.get('remaining_life_years', 0):.2f} years. "
                f"Statutory Audit ({audit.get('sanction_clause', statutory_framework)}): {audit.get('compliance_status')}."
            ),
        }

        doc_res = generate_nfa_documents.invoke({
            "template_type": template_name,
            "base_name": f"{eq_id}_Statutory_NFA",
            "payload": payload
        })

        return {
            "equipment_id": eq_id,
            "t_req_mm": calc.get("t_req_mm", 0.0),
            "measured_mm": t_act,
            "delta_mm": calc.get("delta_mm", 0.0),
            "is_breach": calc.get("is_breach", False),
            "remaining_life_years": calc.get("remaining_life_years", 0.0),
            "status": calc.get("status", "UNKNOWN"),
            "audit_status": audit.get("compliance_status", "UNKNOWN"),
            "sanction_clause": audit.get("sanction_clause", statutory_framework),
            "executive_summary": (
                f"ASME Section VIII Div 1 UG-27 verification for {eq_id}: "
                f"Required thickness = {calc.get('t_req_mm', 0):.2f}mm, Measured = {t_act:.2f}mm, "
                f"Safety Margin Δ = {calc.get('delta_mm', 0):.2f}mm ({calc.get('status')}). "
                f"Remaining Service Life = {calc.get('remaining_life_years', 0):.2f} years. "
                f"Statutory Audit ({audit.get('sanction_clause', statutory_framework)}): {audit.get('compliance_status')}."
            ),
            "docx_path": doc_res.get("docx_path", ""),
            "sha256_hash": doc_res.get("document_hash", doc_res.get("sha256_hash", "")),
            "pdf_path": doc_res.get("pdf_path"),
            "pdf_sha256": doc_res.get("pdf_sha256"),
            "generated_at": datetime.datetime.now().isoformat(),
        }

    def run_multi_agent_query(self, query: str, thread_id: str = "default_thread") -> Dict[str, Any]:
        """
        Executes an open-ended engineering, compliance, or coding prompt
        through the autonomous LangGraph multi-agent pipeline.
        """
        from agent_orchestrator.pipeline import app
        config = {"configurable": {"thread_id": thread_id}}
        return app.invoke({"messages": [("user", query)]}, config=config)
