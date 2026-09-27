from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict

try:
    from docx import Document
except ImportError as exc:  # pragma: no cover
    Document = None
    _DOCX_IMPORT_ERROR = exc
else:
    _DOCX_IMPORT_ERROR = None

try:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import Paragraph, Spacer, SimpleDocTemplate, Table, TableStyle
    from reportlab.lib import colors
except ImportError as exc:  # pragma: no cover
    A4 = None
    getSampleStyleSheet = None
    mm = None
    Paragraph = None
    Spacer = None
    SimpleDocTemplate = None
    Table = None
    TableStyle = None
    colors = None
    _PDF_IMPORT_ERROR = exc
else:
    _PDF_IMPORT_ERROR = None

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "data" / "output"


def _to_display(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _safe_filename(base_name: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in base_name)
    return cleaned.strip("._") or "approval_note"


def _build_integrity_hash(inspection_data: Dict[str, Any], calculation_data: Dict[str, Any], compliance_data: Dict[str, Any], executive_summary: str) -> str:
    payload = {
        "inspection_data": inspection_data or {},
        "calculation_data": calculation_data or {},
        "compliance_data": compliance_data or {},
        "executive_summary": executive_summary or "",
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _write_docx_document(file_path: Path, inspection_data: Dict[str, Any], calculation_data: Dict[str, Any], compliance_data: Dict[str, Any], executive_summary: str, integrity_hash: str):
    if Document is None:
        raise ImportError("python-docx is required for DOCX generation.") from _DOCX_IMPORT_ERROR

    document = Document()
    document.add_heading("PSU NOTES FOR APPROVAL (NFA)", level=1)
    document.add_paragraph("Classification: INTERNAL / PSU APPROVAL NOTE")
    document.add_paragraph("Status: GENERATED LOCALLY - AIR-GAPPED / OFFLINE")
    document.add_paragraph(f"Integrity Seal (SHA-256): {integrity_hash}")

    metadata = [
        ("Equipment ID", inspection_data.get("equipment_id", "N/A")),
        ("Equipment Name", inspection_data.get("equipment_name", "N/A")),
        ("Material", inspection_data.get("material", "N/A")),
        ("Inspection Date", inspection_data.get("inspection_date", "N/A")),
        ("Location", inspection_data.get("location", "N/A")),
    ]
    table = document.add_table(rows=1, cols=2)
    table.style = "Table Grid"
    table.rows[0].cells[0].text = "Field"
    table.rows[0].cells[1].text = "Value"
    for key, value in metadata:
        row = table.add_row().cells
        row[0].text = key
        row[1].text = _to_display(value)

    document.add_paragraph()
    document.add_heading("Engineering Calculation Summary", level=2)
    calc_table = document.add_table(rows=1, cols=2)
    calc_table.style = "Table Grid"
    calc_table.rows[0].cells[0].text = "Metric"
    calc_table.rows[0].cells[1].text = "Value"
    calc_rows = [
        ("Design Pressure (MPa)", calculation_data.get("design_pressure_mpa", "N/A")),
        ("Measured Thickness (mm)", calculation_data.get("measured_thickness_mm", "N/A")),
        ("Required Thickness (mm)", calculation_data.get("t_req_mm", "N/A")),
        ("Delta (mm)", calculation_data.get("delta_mm", "N/A")),
        ("Corrosion Rate (mm/yr)", calculation_data.get("corrosion_rate_mm_yr", "N/A")),
        ("Remaining Life (years)", calculation_data.get("remaining_life_years", "N/A")),
        ("Status", calculation_data.get("status", "N/A")),
    ]
    for key, value in calc_rows:
        row = calc_table.add_row().cells
        row[0].text = key
        row[1].text = _to_display(value)

    document.add_paragraph()
    document.add_heading("CVC / Compliance Review", level=2)
    for key, value in [
        ("Applicable Clause", compliance_data.get("applicable_clause", "N/A")),
        ("Clause Summary", compliance_data.get("clause_summary", "N/A")),
        ("Procurement Route", compliance_data.get("procurement_route", "N/A")),
        ("Approval Status", compliance_data.get("approval_status", "N/A")),
    ]:
        document.add_paragraph(f"{key}: {_to_display(value)}")

    document.add_paragraph()
    document.add_heading("Executive Summary", level=2)
    document.add_paragraph(executive_summary or "No executive summary provided.")

    document.add_paragraph()
    document.add_paragraph("This approval note is generated for internal engineering review and approval workflow only.")
    document.save(file_path)


def _write_pdf_document(file_path: Path, inspection_data: Dict[str, Any], calculation_data: Dict[str, Any], compliance_data: Dict[str, Any], executive_summary: str, integrity_hash: str):
    if SimpleDocTemplate is None:
        raise ImportError("reportlab is required for PDF generation.") from _PDF_IMPORT_ERROR

    styles = getSampleStyleSheet()
    story = []
    story.append(Paragraph("PSU NOTES FOR APPROVAL (NFA)", styles["Title"]))
    story.append(Paragraph("Classification: INTERNAL / PSU APPROVAL NOTE", styles["Normal"]))
    story.append(Paragraph("Status: GENERATED LOCALLY - AIR-GAPPED / OFFLINE", styles["Normal"]))
    story.append(Paragraph(f"Integrity Seal (SHA-256): {integrity_hash}", styles["Normal"]))
    story.append(Spacer(1, 10 * mm))

    items = [
        ("Equipment ID", inspection_data.get("equipment_id", "N/A")),
        ("Equipment Name", inspection_data.get("equipment_name", "N/A")),
        ("Material", inspection_data.get("material", "N/A")),
        ("Inspection Date", inspection_data.get("inspection_date", "N/A")),
        ("Location", inspection_data.get("location", "N/A")),
        ("Design Pressure (MPa)", calculation_data.get("design_pressure_mpa", "N/A")),
        ("Measured Thickness (mm)", calculation_data.get("measured_thickness_mm", "N/A")),
        ("Required Thickness (mm)", calculation_data.get("t_req_mm", "N/A")),
        ("Delta (mm)", calculation_data.get("delta_mm", "N/A")),
        ("status", calculation_data.get("status", "N/A")),
        ("Applicable Clause", compliance_data.get("applicable_clause", "N/A")),
        ("Procurement Route", compliance_data.get("procurement_route", "N/A")),
    ]

    table_data = [["Field", "Value"]]
    for key, value in items:
        table_data.append([key, _to_display(value)])

    table = Table(table_data, colWidths=[70 * mm, 100 * mm])
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#D9E2F3")),
            ("GRID", (0, 0), (-1, -1), 0.8, colors.grey),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ])
    )
    story.append(table)
    story.append(Spacer(1, 10 * mm))
    story.append(Paragraph("Executive Summary", styles["Heading2"]))
    story.append(Paragraph(executive_summary or "No executive summary provided.", styles["Normal"]))

    doc = SimpleDocTemplate(str(file_path), pagesize=A4)
    doc.build(story)


def deliverable_publisher_tool(
    inspection_data: Dict[str, Any],
    calculation_data: Dict[str, Any],
    compliance_data: Dict[str, Any],
    executive_summary: str,
) -> Dict[str, Any]:
    """Creates a local .docx and .pdf approval note bundle with a SHA-256 integrity seal."""
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        equipment_id = _safe_filename(str(inspection_data.get("equipment_id", "UNKNOWN")))
        base_name = f"{equipment_id}_Approval_Note"
        docx_path = OUTPUT_DIR / f"{base_name}.docx"
        pdf_path = OUTPUT_DIR / f"{base_name}.pdf"

        integrity_hash = _build_integrity_hash(
            inspection_data=inspection_data or {},
            calculation_data=calculation_data or {},
            compliance_data=compliance_data or {},
            executive_summary=executive_summary or "",
        )

        _write_docx_document(docx_path, inspection_data or {}, calculation_data or {}, compliance_data or {}, executive_summary or "", integrity_hash)
        _write_pdf_document(pdf_path, inspection_data or {}, calculation_data or {}, compliance_data or {}, executive_summary or "", integrity_hash)

        return {
            "docx_path": docx_path.relative_to(PROJECT_ROOT).as_posix(),
            "pdf_path": pdf_path.relative_to(PROJECT_ROOT).as_posix(),
            "sha256_hash": integrity_hash,
        }
    except Exception as exc:
        return {"status": "ERROR", "message": str(exc)}


if __name__ == "__main__":
    sample_inspection = {
        "equipment_id": "11-V-102",
        "equipment_name": "HP Separator Drum",
        "material": "2.25Cr-1Mo",
        "inspection_date": "2026-09-20",
        "location": "PSU Refinery",
    }
    sample_calculation = {
        "design_pressure_mpa": 14.5,
        "measured_thickness_mm": 138.2,
        "t_req_mm": 138.5,
        "delta_mm": -0.3,
        "corrosion_rate_mm_yr": 0.75,
        "remaining_life_years": 2.4,
        "status": "ALERT",
    }
    sample_compliance = {
        "applicable_clause": "CVC Circular 02/02/2004 Clause 4.2",
        "clause_summary": "Single-source emergency approval route considered valid for safety-critical component replacement.",
        "procurement_route": "Emergency procurement with engineering approval",
        "approval_status": "Pending PSU approval",
    }
    sample_summary = "The vessel remains within the minimum design envelope with a narrow thickness margin. The integrity decision requires engineering review and endorsement before work authorization."
    print(deliverable_publisher_tool(sample_inspection, sample_calculation, sample_compliance, sample_summary))
