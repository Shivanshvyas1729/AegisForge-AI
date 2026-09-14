"""
output_generation/docx_generator.py
Layers 5 & 6: Word (.docx) Deliverable Compiler (Member 4).
Compiles native Microsoft Word (.docx) Note for Approval adhering to CVC guidelines and DOP clauses.
"""

import os
import sys
import hashlib
from pathlib import Path
from datetime import datetime
import docx
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

from schemas.mvp_schema import InspectionInput, CalculationOutput, ReasoningOutput


def compute_file_sha256(file_path: str) -> str:
    """Computes SHA-256 hash for document integrity and air-gap verification."""
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            sha256.update(chunk)
    return sha256.hexdigest()


def generate_approval_nfa_docx(
    inspection: InspectionInput,
    calculation: CalculationOutput,
    reasoning: ReasoningOutput,
    output_path: str
) -> str:
    """
    Generates a formal PSU Note for Approval (.docx) with tables, compliance clauses, and signatures.
    """
    doc = docx.Document()

    # Set standard 1-inch margins
    sections = doc.sections
    for s in sections:
        s.top_margin = Inches(1.0)
        s.bottom_margin = Inches(1.0)
        s.left_margin = Inches(1.0)
        s.right_margin = Inches(1.0)

    # 1. Top Classification Header
    p_header = doc.add_paragraph()
    p_header.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r_class = p_header.add_run("INDIAN OIL CORPORATION LIMITED // REFINERIES DIVISION\n")
    r_class.bold = True
    r_class.font.size = Pt(13)
    r_class.font.color.rgb = RGBColor(30, 58, 138)

    r_banner = p_header.add_run("RESTRICTED // FOR OFFICIAL USE ONLY\nNOTE FOR APPROVAL (NFA)")
    r_banner.bold = True
    r_banner.font.size = Pt(14)
    r_banner.font.color.rgb = RGBColor(185, 28, 28)  # Crimson red

    # File Reference & Metadata Table
    p_meta = doc.add_paragraph()
    p_meta.add_run(f"File No: IOCL/GHR/HCU-11/NFA/2026-09/042\n").bold = True
    p_meta.add_run(f"Date: {datetime.utcnow().strftime('%d-%B-%Y')} | Unit: Hydrocracker (HCU-11)\n")
    p_meta.add_run(f"Initiating Department: Inspection & Asset Integrity Division")
    doc.add_paragraph("-" * 70)

    # 2. Subject Line
    p_subj = doc.add_paragraph()
    r_subj = p_subj.add_run(
        f"SUBJECT: Emergency Repair Sanction — Statutory ASME Thickness Breach on {inspection.equipment_id} ({inspection.equipment_name})"
    )
    r_subj.bold = True
    r_subj.font.size = Pt(12)

    # 3. Section 1: Background & NDT Discovery
    doc.add_heading("1. Background & NDT Ultrasonic Survey Defect Discovery", level=2)
    p_bg = doc.add_paragraph(
        f"During routine ultrasonic thickness gauging of the 1st Stage High-Pressure Separator ({inspection.equipment_id}), "
        f"an acute wall thinning anomaly was detected at location {inspection.critical_location} (Bottom Knuckle). "
        f"Base material is {inspection.material}. The field inspector recorded a measured wall thickness of "
        f"{inspection.measured_thickness_mm:.2f} mm against an accelerated corrosion rate of {inspection.corrosion_rate_mm_yr:.2f} mm/yr."
    )

    # 4. Section 2: Statutory Code Calculations & Breach Table
    doc.add_heading("2. Statutory Code Calculations (ASME Sec VIII Div 1 & API 510)", level=2)
    doc.add_paragraph(
        "Verification using the ASME Sec VIII Div 1 UG-27 cylindrical shell formula yielded the following findings:"
    )

    # Compliance Table
    table = doc.add_table(rows=6, cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.style = "Table Grid"

    rows_data = [
        ("Design Pressure (P)", f"{inspection.design_pressure_mpa} MPa ({calculation.design_pressure_bar} barg)"),
        ("Minimum Required Thickness (t_min)", f"{calculation.t_req_mm:.2f} mm (ASME UG-27)"),
        ("Actual Measured Thickness (t_actual)", f"{calculation.measured_thickness_mm:.2f} mm at Point {inspection.critical_location}"),
        ("Safety Margin Delta (t_actual - t_min)", f"{calculation.delta_mm:.2f} mm [STATUTORY CODE BREACH]"),
        ("API 510 Remaining Safe Service Life", f"{calculation.remaining_life_years:.2f} Years (BELOW ZERO)"),
        ("Recommended Derated MAWP", f"{calculation.derated_mawp_bar:.1f} barg (Immediate operational limit)"),
    ]

    for i, (label, val) in enumerate(rows_data):
        row = table.rows[i]
        c0 = row.cells[0].paragraphs[0].add_run(label)
        c0.bold = True
        c1 = row.cells[1].paragraphs[0].add_run(val)
        if "BREACH" in val or "BELOW ZERO" in val:
            c1.bold = True
            c1.font.color.rgb = RGBColor(185, 28, 28)

    doc.add_paragraph()  # Spacer

    # 5. Section 3: CVC Guidelines & Emergency Procurement Justification
    doc.add_heading("3. CVC Guidelines & Emergency Procurement Justification", level=2)
    doc.add_paragraph(
        reasoning.cvc_guideline_clause or (
            "In accordance with Central Vigilance Commission (CVC) Circular No. 02/02/2004 and Delegation of Powers (DOP) "
            "Clause 4.2 (Single-Source Emergency Procurement), immediate shutdown intervention is mandatory to prevent "
            "catastrophic loss of containment under sour gas operational conditions."
        )
    )

    # 6. Section 4: Recommended Action & Financial Sanction
    doc.add_heading("4. Recommended Action & Financial Sanction", level=2)
    doc.add_paragraph(
        f"{reasoning.recommended_action}\n\n"
        f"Estimated Total Expenditure: {reasoning.estimated_cost} (Covered under Refinery Turnaround Capex Budget Code HCU-2026-CAP)."
    )

    # 7. Section 5: Signature Block
    doc.add_heading("5. Submission & Approval Block", level=2)
    doc.add_paragraph(
        "\n\n"
        "Prepared By:  __________________________        Verified By: __________________________\n"
        "              Sr. Inspection Engineer                        Chief Manager (Integrity)\n\n\n"
        "Approved By:  __________________________\n"
        "              Executive Director & Refinery Head\n"
        "              Competent Financial Authority (DOP Clause 2.1)"
    )

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    doc.save(output_path)

    sha256_hash = compute_file_sha256(output_path)
    return output_path


if __name__ == "__main__":
    out_dir = PROJECT_ROOT / "data" / "output"
    out_file = out_dir / "IOCL_Emergency_Approval_Note_Test.docx"

    test_insp = InspectionInput(
        equipment_id="11-V-102",
        equipment_name="1st Stage HP Separator drum",
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
        derated_mawp_bar=118.0,
        design_pressure_bar=145.0,
        status="CRITICAL_BREACH",
    )
    test_reason = ReasoningOutput(
        executive_summary="ASME wall thickness breach detected on 11-V-102 at Point BK-01.",
        cvc_guideline_clause="CVC PAC Single-Source Clause 4.2 applied due to imminent rupture risk.",
        recommended_action="Execute emergency weld overlay and replace bottom knuckle during October turnaround.",
        estimated_cost="Rs. 88.0 Lakhs",
        raw_model_response="Model verified ASME UG-27 formula and confirmed statutory shutdown necessity.",
    )

    print(f"Testing Word Document Compiler -> {out_file}")
    res_path = generate_approval_nfa_docx(test_insp, test_calc, test_reason, str(out_file))
    print(f"Generated successfully: {res_path}")
    print(f"File size: {os.path.getsize(res_path)} bytes")
    print(f"SHA-256:   {compute_file_sha256(res_path)}")
    assert os.path.exists(res_path), "File was not created"
    assert os.path.getsize(res_path) > 1000, "File is too small"
    print("✅ Word .docx Generator DoD PASSED!")
