"""
output_generation/pdf_generator.py
Layers 5 & 6: PDF Deliverable Compiler.
Compiles native PDF Note for Approval adhering to CVC guidelines, ASME Section VIII calculations, and DOP clauses.
Uses ReportLab with high-fidelity corporate formatting, tables, color-coded breach markers, and signature blocks.
"""

import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Optional

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

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    HRFlowable,
    KeepTogether,
)


def compute_file_sha256(file_path: str) -> str:
    """Computes SHA-256 hash for document integrity and air-gap verification."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_approval_nfa_pdf(
    inspection: InspectionInput,
    calculation: CalculationOutput,
    reasoning: ReasoningOutput,
    output_path: str
) -> str:
    """
    Generates a formal PSU Note for Approval (.pdf) with tables, compliance clauses, and signatures.
    Returns the absolute path to the generated PDF.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    # Custom typography styles
    style_header_corp = ParagraphStyle(
        name="HeaderCorp",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=12,
        leading=15,
        alignment=1,  # Center
        textColor=colors.HexColor("#1e3a8a"),  # Deep Navy Blue
    )

    style_banner_conf = ParagraphStyle(
        name="BannerConf",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=13,
        leading=16,
        alignment=1,  # Center
        textColor=colors.HexColor("#b91c1c"),  # Crimson Red
    )

    style_meta = ParagraphStyle(
        name="MetaInfo",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#374151"),
    )

    style_subj = ParagraphStyle(
        name="SubjectLine",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#111827"),
    )

    style_heading = ParagraphStyle(
        name="SectionHeading",
        parent=styles["Heading2"],
        fontName="Helvetica-Bold",
        fontSize=11,
        leading=14,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=8,
        spaceAfter=4,
    )

    style_body = ParagraphStyle(
        name="BodyTextCustom",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=9,
        leading=13,
        textColor=colors.HexColor("#1f2937"),
        alignment=4,  # Justify
    )

    style_table_header = ParagraphStyle(
        name="TableHeader",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.white,
    )

    style_table_cell = ParagraphStyle(
        name="TableCell",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#111827"),
    )

    style_table_breach = ParagraphStyle(
        name="TableBreachCell",
        parent=styles["Normal"],
        fontName="Helvetica-Bold",
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#b91c1c"),
    )

    style_signature = ParagraphStyle(
        name="SigText",
        parent=styles["Normal"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#374151"),
    )

    story = []

    # 1. Top Header
    story.append(Paragraph("INDIAN OIL CORPORATION LIMITED // REFINERIES DIVISION", style_header_corp))
    story.append(Spacer(1, 3))
    story.append(Paragraph("RESTRICTED // FOR OFFICIAL USE ONLY<br/>NOTE FOR APPROVAL (NFA)", style_banner_conf))
    story.append(Spacer(1, 6))

    # Metadata Block
    meta_text = (
        f"<b>File No:</b> IOCL/GHR/HCU-11/NFA/2026-09/042 &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Date:</b> {datetime.now().strftime('%d-%B-%Y')} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"<b>Unit:</b> Hydrocracker (HCU-11)<br/>"
        f"<b>Initiating Department:</b> Inspection & Asset Integrity Division"
    )
    story.append(Paragraph(meta_text, style_meta))
    story.append(Spacer(1, 4))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#9ca3af"), spaceAfter=6, spaceBefore=2))

    # 2. Subject Line
    subj_text = f"<b>SUBJECT: Emergency Repair Sanction — Statutory ASME Thickness Breach on {inspection.equipment_id} ({inspection.equipment_name})</b>"
    story.append(Paragraph(subj_text, style_subj))
    story.append(Spacer(1, 6))

    # 3. Section 1: Background & NDT Discovery
    story.append(Paragraph("1. Background & NDT Ultrasonic Survey Defect Discovery", style_heading))
    bg_text = (
        f"During routine ultrasonic thickness gauging of the 1st Stage High-Pressure Separator "
        f"({inspection.equipment_id}), an acute wall thinning anomaly was detected at location "
        f"<b>{inspection.critical_location}</b> (Bottom Knuckle). Base material is <b>{inspection.material}</b>. "
        f"The field inspector recorded a measured wall thickness of <b>{inspection.measured_thickness_mm:.2f} mm</b> "
        f"against an accelerated corrosion rate of <b>{inspection.corrosion_rate_mm_yr:.2f} mm/yr</b>."
    )
    story.append(Paragraph(bg_text, style_body))
    story.append(Spacer(1, 6))

    # 4. Section 2: Statutory Code Calculations & Breach Table
    story.append(Paragraph("2. Statutory Code Calculations (ASME Sec VIII Div 1 & API 510)", style_heading))
    story.append(Paragraph(
        "Verification using the ASME Sec VIII Div 1 UG-27 cylindrical shell formula yielded the following findings:",
        style_body
    ))
    story.append(Spacer(1, 4))

    if calculation.remaining_life_years is None:
        life_str = "N/A (Zero corrosion rate - no degradation)"
        life_style = style_table_cell
    elif calculation.remaining_life_years < 0:
        life_str = f"{calculation.remaining_life_years:.2f} Years (BELOW ZERO)"
        life_style = style_table_breach
    else:
        life_str = f"{calculation.remaining_life_years:.2f} Years"
        life_style = style_table_cell

    delta_str = f"{calculation.delta_mm:.2f} mm [STATUTORY CODE BREACH]" if calculation.is_breach else f"{calculation.delta_mm:.2f} mm [SAFE]"
    delta_style = style_table_breach if calculation.is_breach else style_table_cell

    # Table data
    t_rows = [
        [Paragraph("Parameter / Statutory Metric", style_table_header), Paragraph("Engineering Finding & Status", style_table_header)],
        [Paragraph("Design Pressure (P)", style_table_cell), Paragraph(f"{inspection.design_pressure_mpa} MPa ({calculation.design_pressure_bar} barg)", style_table_cell)],
        [Paragraph("Minimum Required Thickness (t_min)", style_table_cell), Paragraph(f"{calculation.t_req_mm:.2f} mm (ASME UG-27)", style_table_cell)],
        [Paragraph("Actual Measured Thickness (t_actual)", style_table_cell), Paragraph(f"{calculation.measured_thickness_mm:.2f} mm at Point {inspection.critical_location}", style_table_cell)],
        [Paragraph("Safety Margin Delta (t_actual - t_min)", style_table_cell), Paragraph(delta_str, delta_style)],
        [Paragraph("API 510 Remaining Safe Service Life", style_table_cell), Paragraph(life_str, life_style)],
        [Paragraph("Recommended Derated MAWP", style_table_cell), Paragraph(f"{calculation.derated_mawp_bar:.1f} barg (Immediate operational limit)", style_table_cell)],
    ]

    t = Table(t_rows, colWidths=[2.7 * inch, 4.3 * inch])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#1e3a8a")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f9fafb")]),
    ]))
    story.append(t)
    story.append(Spacer(1, 6))

    # 5. Section 3: CVC Guidelines
    story.append(Paragraph("3. CVC Guidelines & Emergency Procurement Justification", style_heading))
    cvc_text = reasoning.cvc_guideline_clause or (
        "In accordance with Central Vigilance Commission (CVC) Circular No. 02/02/2004 and Delegation of Powers (DOP) "
        "Clause 4.2 (Single-Source Emergency Procurement), immediate shutdown intervention is mandatory to prevent "
        "catastrophic loss of containment under sour gas operational conditions."
    )
    story.append(Paragraph(cvc_text, style_body))
    story.append(Spacer(1, 6))

    # 6. Section 4: Recommended Action
    story.append(Paragraph("4. Recommended Action & Financial Sanction", style_heading))
    action_text = (
        f"{reasoning.recommended_action}<br/><br/>"
        f"<b>Estimated Total Expenditure:</b> {reasoning.estimated_cost} "
        f"(Covered under Refinery Turnaround Capex Budget Code HCU-2026-CAP)."
    )
    story.append(Paragraph(action_text, style_body))
    story.append(Spacer(1, 8))

    # 7. Section 5: Signature Block
    sig_content = []
    sig_content.append(Paragraph("5. Submission & Approval Block", style_heading))
    sig_table_data = [
        [
            Paragraph("<b>Prepared By:</b><br/><br/>___________________________<br/>Sr. Inspection Engineer<br/>Emp ID: 448102", style_signature),
            Paragraph("<b>Verified By:</b><br/><br/>___________________________<br/>Chief Manager (Integrity)<br/>Emp ID: 310294", style_signature),
            Paragraph("<b>Approved By:</b><br/><br/>___________________________<br/>Executive Director & Refinery Head<br/>Competent Financial Authority (DOP 2.1)", style_signature),
        ]
    ]
    sig_table = Table(sig_table_data, colWidths=[2.33 * inch, 2.33 * inch, 2.33 * inch])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#d1d5db")),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
    ]))
    sig_content.append(sig_table)

    story.append(KeepTogether(sig_content))

    doc.build(story)

    sha256_hash = compute_file_sha256(output_path)
    return output_path


if __name__ == "__main__":
    test_insp = InspectionInput(
        equipment_id="11-V-102",
        equipment_name="HP Separator Drum",
        material="2.25Cr-1Mo + 347 SS cladding",
        design_pressure_mpa=14.5,
        inside_radius_mm=1200.0,
        allowable_stress_mpa=138.0,
        joint_efficiency=1.0,
        corrosion_allowance_mm=4.0,
        critical_location="BK-01",
        measured_thickness_mm=138.20,
        corrosion_rate_mm_yr=0.75,
    )
    test_calc = CalculationOutput(
        t_req_mm=138.57,
        measured_thickness_mm=138.20,
        delta_mm=-0.37,
        is_breach=True,
        remaining_life_years=-0.49,
        derated_mawp_bar=144.6,
        design_pressure_bar=145.0,
        status="CRITICAL_BREACH",
    )
    test_reason = ReasoningOutput(
        executive_summary="ASME Sec VIII Div 1 breach on vessel 11-V-102.",
        cvc_guideline_clause="CVC Circular No. 02/02/2004 emergency single-source procurement applies.",
        recommended_action="Emergency single-source procurement of Inconel 625 weld overlay repair.",
        estimated_cost="Rs. 88.0 Lakhs",
        raw_model_response="Raw DeepSeek-R1 synthesis output.",
    )

    out_file = PROJECT_ROOT / "data" / "output" / "IOCL_Emergency_Approval_Note_Test.pdf"
    res_path = generate_approval_nfa_pdf(test_insp, test_calc, test_reason, str(out_file))
    print(f"Generated PDF: {res_path}")
    print(f"Size: {os.path.getsize(res_path)} bytes")
    print(f"SHA-256: {compute_file_sha256(res_path)}")
    print("✅ PDF Generator DoD PASSED!")
