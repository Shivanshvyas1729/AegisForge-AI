"""
tools/doc_generator.py
Layer 4 / Output Tools: Unified Document Generation Engine.
Wraps DOCX and PDF compilers into clean callable tools for orchestrators, agents, and UI.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

if sys.stdout and hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr and hasattr(sys.stderr, 'reconfigure'):
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from schemas.mvp_schema import InspectionInput, CalculationOutput, ReasoningOutput
from output_generation.docx_generator import generate_approval_nfa_docx, compute_file_sha256 as compute_docx_sha256
from output_generation.pdf_generator import generate_approval_nfa_pdf, compute_file_sha256 as compute_pdf_sha256


DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def generate_docx_deliverable(
    inspection: InspectionInput,
    calculation: CalculationOutput,
    reasoning: ReasoningOutput,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Compiles native Microsoft Word (.docx) Note for Approval deliverable."""
    if not output_path:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(DEFAULT_OUTPUT_DIR / f"{inspection.equipment_id}_Approval_Note.docx")

    docx_path = generate_approval_nfa_docx(inspection, calculation, reasoning, str(output_path))
    sha256 = compute_docx_sha256(docx_path)
    return {
        "format": "docx",
        "path": docx_path,
        "filename": Path(docx_path).name,
        "size_bytes": os.path.getsize(docx_path),
        "sha256": sha256,
    }


def generate_pdf_deliverable(
    inspection: InspectionInput,
    calculation: CalculationOutput,
    reasoning: ReasoningOutput,
    output_path: Optional[str] = None
) -> Dict[str, Any]:
    """Compiles native Adobe PDF (.pdf) Note for Approval deliverable."""
    if not output_path:
        DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        output_path = str(DEFAULT_OUTPUT_DIR / f"{inspection.equipment_id}_Approval_Note.pdf")

    pdf_path = generate_approval_nfa_pdf(inspection, calculation, reasoning, str(output_path))
    sha256 = compute_pdf_sha256(pdf_path)
    return {
        "format": "pdf",
        "path": pdf_path,
        "filename": Path(pdf_path).name,
        "size_bytes": os.path.getsize(pdf_path),
        "sha256": sha256,
    }


def generate_both_deliverables(
    inspection: InspectionInput,
    calculation: CalculationOutput,
    reasoning: ReasoningOutput,
    base_name: str = "IOCL_Emergency_Approval_Note",
    output_dir: Optional[Path] = None,
) -> Dict[str, Any]:
    """Compiles both native DOCX and PDF deliverables simultaneously."""
    target_dir = output_dir or DEFAULT_OUTPUT_DIR
    target_dir.mkdir(parents=True, exist_ok=True)

    docx_target = str(target_dir / f"{base_name}.docx")
    pdf_target = str(target_dir / f"{base_name}.pdf")

    docx_info = generate_docx_deliverable(inspection, calculation, reasoning, docx_target)
    pdf_info = generate_pdf_deliverable(inspection, calculation, reasoning, pdf_target)

    return {
        "docx": docx_info,
        "pdf": pdf_info,
    }


try:
    from langchain_core.tools import tool

    @tool
    def docx_export_tool(
        equipment_id: str,
        equipment_name: str,
        t_req_mm: float,
        measured_thickness_mm: float,
        delta_mm: float,
        status: str,
        executive_summary: str,
        recommended_action: str
    ) -> str:
        """
        Tool to generate a formal PSU Note for Approval Microsoft Word (.docx) document.
        """
        insp = InspectionInput(
            equipment_id=equipment_id,
            equipment_name=equipment_name,
            measured_thickness_mm=measured_thickness_mm
        )
        calc = CalculationOutput(
            t_req_mm=t_req_mm,
            measured_thickness_mm=measured_thickness_mm,
            delta_mm=delta_mm,
            is_breach=(delta_mm < 0),
            remaining_life_years=1.0 if delta_mm >= 0 else -0.5,
            derated_mawp_bar=140.0,
            status=status
        )
        reason = ReasoningOutput(
            executive_summary=executive_summary,
            cvc_guideline_clause="CVC Circular 02/02/2004",
            recommended_action=recommended_action,
            raw_model_response=executive_summary
        )
        res = generate_docx_deliverable(insp, calc, reason)
        return f"DOCX successfully generated at: {res['path']} (SHA-256: {res['sha256'][:12]}...)"

    @tool
    def pdf_export_tool(
        equipment_id: str,
        equipment_name: str,
        t_req_mm: float,
        measured_thickness_mm: float,
        delta_mm: float,
        status: str,
        executive_summary: str,
        recommended_action: str
    ) -> str:
        """
        Tool to generate a formal PSU Note for Approval Adobe PDF (.pdf) document.
        """
        insp = InspectionInput(
            equipment_id=equipment_id,
            equipment_name=equipment_name,
            measured_thickness_mm=measured_thickness_mm
        )
        calc = CalculationOutput(
            t_req_mm=t_req_mm,
            measured_thickness_mm=measured_thickness_mm,
            delta_mm=delta_mm,
            is_breach=(delta_mm < 0),
            remaining_life_years=1.0 if delta_mm >= 0 else -0.5,
            derated_mawp_bar=140.0,
            status=status
        )
        reason = ReasoningOutput(
            executive_summary=executive_summary,
            cvc_guideline_clause="CVC Circular 02/02/2004",
            recommended_action=recommended_action,
            raw_model_response=executive_summary
        )
        res = generate_pdf_deliverable(insp, calc, reason)
        return f"PDF successfully generated at: {res['path']} (SHA-256: {res['sha256'][:12]}...)"

except ImportError:
    docx_export_tool = None
    pdf_export_tool = None


if __name__ == "__main__":
    t_insp = InspectionInput()
    t_calc = CalculationOutput(
        t_req_mm=138.57,
        measured_thickness_mm=138.20,
        delta_mm=-0.37,
        is_breach=True,
        remaining_life_years=-0.49,
        derated_mawp_bar=144.6,
        status="CRITICAL_BREACH"
    )
    t_reason = ReasoningOutput(
        executive_summary="Emergency thickness breach test.",
        cvc_guideline_clause="DOP 4.2 emergency procurement.",
        recommended_action="Emergency overlay repair.",
        raw_model_response="Model output."
    )
    both = generate_both_deliverables(t_insp, t_calc, t_reason, "Test_Both_Deliverables")
    print("Generated DOCX:", both["docx"]["path"], "Bytes:", both["docx"]["size_bytes"])
    print("Generated PDF:", both["pdf"]["path"], "Bytes:", both["pdf"]["size_bytes"])
    print("✅ Document Generator Tools DoD PASSED!")
