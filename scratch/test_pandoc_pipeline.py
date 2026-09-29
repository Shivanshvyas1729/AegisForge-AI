import pypandoc
from pathlib import Path
from xhtml2pdf import pisa
import hashlib

output_dir = Path("data/output")
output_dir.mkdir(parents=True, exist_ok=True)

md_file = output_dir / "test_pandoc.md"
docx_file = output_dir / "test_pandoc.docx"
pdf_file = output_dir / "test_pandoc.pdf"

md_text = """# MANGALORE REFINERY & PETROCHEMICALS LTD
**Document:** Statutory Notes for Approval (NFA)
**Vessel Tag:** 11-V-102
**Date:** 2026-09-29

---

## 1. Executive Summary
Ultrasonic thickness evaluation of High-Pressure Separator **11-V-102** identified localized wall thinning below design baseline. Operational derating was assessed per ASME Section VIII Div 1 UG-27 and API 579-1 / ASME FFS-1 Level 1.

## 2. Quantitative Verification Matrix

| Parameter | Required Standard | Evaluated Value | Margin / Delta | Verdict |
| :--- | :--- | :--- | :--- | :--- |
| **Design Pressure (P)** | 14.50 MPa | 14.50 MPa | Nominal | Evaluated |
| **Inside Radius (R)** | 1200.00 mm | 1200.00 mm | Nominal | Evaluated |
| **Allowable Stress (S)**| 138.00 MPa | 138.00 MPa | SA-387 Gr 22 | Verified |
| **Joint Efficiency (E)**| 1.00 | 1.00 | 100% RT | Full Radiography |
| **Corrosion Allowance** | 4.00 mm | 4.00 mm | Specified | Verified |
| **Required Thickness** | 138.57 mm | - | Baseline | Statutory Min |
| **Measured Thickness** | - | 138.20 mm | -0.37 mm | **DEFICIT** |
| **Derated MAWP** | 14.50 MPa | 14.46 MPa | -0.04 MPa | **DERATED SAFE** |

> **Operational Directive (Human Gate):**
> Operational sign-off authorized for 11-V-102 under derated pressure of 14.46 MPa with mandatory 6-month NDT re-inspection schedule per API 579 Level 1 Assessment.

## 3. Statutory Procurement Compliance (CVC / GFR 2017)
1. Single-source emergency replacement justified under statutory emergency provisions (GFR 2017 Rule 194).
2. Cost estimate of 18.5 Lakhs falls within Delegation of Powers (DoP) for General Manager approval.
3. No vigilance anomalies detected.
"""

with open(md_file, "w", encoding="utf-8") as f:
    f.write(md_text)

print("1. MD written successfully:", md_file.exists(), md_file.stat().st_size, "bytes")

# Convert to DOCX using pypandoc
pypandoc.convert_file(str(md_file), "docx", format="md", outputfile=str(docx_file))
print("2. DOCX created successfully:", docx_file.exists(), docx_file.stat().st_size, "bytes")

# Convert to PDF via HTML using pypandoc + xhtml2pdf
html_body = pypandoc.convert_file(str(md_file), "html", format="md")
styled_html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
@page {{ size: a4 portrait; margin: 20mm; }}
body {{ font-family: Helvetica, Arial, sans-serif; font-size: 10pt; line-height: 1.5; color: #1e293b; }}
h1 {{ color: #0f172a; font-size: 18pt; border-bottom: 2px solid #2563eb; padding-bottom: 4px; margin-bottom: 12px; }}
h2 {{ color: #1e3a8a; font-size: 13pt; margin-top: 14px; margin-bottom: 6px; border-bottom: 1px solid #e2e8f0; }}
table {{ width: 100%; border-collapse: collapse; margin: 12px 0; }}
th, td {{ border: 1px solid #cbd5e1; padding: 6px 8px; text-align: left; font-size: 9pt; }}
th {{ background-color: #f1f5f9; font-weight: bold; color: #0f172a; }}
blockquote {{ background: #f8fafc; border-left: 4px solid #f59e0b; padding: 8px 12px; margin: 10px 0; font-style: italic; }}
hr {{ border: 0; border-top: 1px solid #cbd5e1; margin: 12px 0; }}
code {{ font-family: Courier, monospace; background: #f1f5f9; padding: 1px 4px; }}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

with open(pdf_file, "wb") as f_pdf:
    status = pisa.CreatePDF(styled_html, dest=f_pdf)

print("3. PDF created successfully:", pdf_file.exists(), pdf_file.stat().st_size, "bytes", "pisa err:", status.err)

# SHA-256 seal
h = hashlib.sha256(docx_file.read_bytes()).hexdigest()
print("4. SHA-256 Hash:", h)
