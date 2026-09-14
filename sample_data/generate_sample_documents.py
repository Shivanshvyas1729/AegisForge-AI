#!/usr/bin/env python3
"""
================================================================================
AEGISFORGE-AI: NATIVE OFFICE DOCUMENT GENERATOR (.DOCX, .XLSX, .PPTX)
Dependencies: Pure Python Standard Library (zipfile, os) - ZERO EXTERNAL PIP PACKAGES
Purpose: Generates valid Microsoft Office OpenXML (.docx, .xlsx, .pptx) test fixtures
         representing real-world PSU/Refinery knowledge work deliverables.
================================================================================
"""

import os
import zipfile


def create_docx(file_path: str, title: str, subtitle: str, paragraphs: list):
    """Generates a valid OpenXML .docx file using standard library zipfile."""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>"""

    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>"""

    doc_paragraphs = []
    # Title
    doc_paragraphs.append(f"""<w:p>
      <w:pPr><w:jc w:val="center"/><w:spacing w:before="240" w:after="120"/></w:pPr>
      <w:r><w:rPr><w:b/><w:sz w:val="36"/><w:color w:val="0B132B"/></w:rPr><w:t>{title}</w:t></w:r>
    </w:p>""")
    # Subtitle
    if subtitle:
        doc_paragraphs.append(f"""<w:p>
          <w:pPr><w:jc w:val="center"/><w:spacing w:before="0" w:after="240"/></w:pPr>
          <w:r><w:rPr><w:i/><w:sz w:val="24"/><w:color w:val="415A77"/></w:rPr><w:t>{subtitle}</w:t></w:r>
        </w:p>""")

    for p in paragraphs:
        if p.startswith("### "):
            header_text = p.replace("### ", "")
            doc_paragraphs.append(f"""<w:p>
              <w:pPr><w:spacing w:before="200" w:after="80"/></w:pPr>
              <w:r><w:rPr><w:b/><w:sz w:val="26"/><w:color w:val="1C2541"/></w:rPr><w:t>{header_text}</w:t></w:r>
            </w:p>""")
        elif p.startswith("## "):
            header_text = p.replace("## ", "")
            doc_paragraphs.append(f"""<w:p>
              <w:pPr><w:spacing w:before="280" w:after="100"/></w:pPr>
              <w:r><w:rPr><w:b/><w:sz w:val="30"/><w:color w:val="0077B6"/></w:rPr><w:t>{header_text}</w:t></w:r>
            </w:p>""")
        else:
            clean_p = p.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            doc_paragraphs.append(f"""<w:p>
              <w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr>
              <w:r><w:rPr><w:sz w:val="22"/><w:color w:val="333333"/></w:rPr><w:t>{clean_p}</w:t></w:r>
            </w:p>""")

    body_content = "\n".join(doc_paragraphs)
    document_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>
    {body_content}
    <w:sectPr>
      <w:pgSz w:w="11906" w:h="16838"/>
      <w:pgMar w:top="1440" w:right="1440" w:bottom="1440" w:left="1440"/>
    </w:sectPr>
  </w:body>
</w:document>"""

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)
    print(f"[+] Created Word Document: {file_path}")


def create_xlsx(file_path: str, sheet_name: str, rows: list):
    """Generates a valid OpenXML .xlsx spreadsheet using standard library zipfile."""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
  <Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

    wb_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>"""

    workbook_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <sheets>
    <sheet name="{sheet_name}" sheetId="1" r:id="rId1"/>
  </sheets>
</workbook>"""

    # Build rows XML
    sheet_data_rows = []
    col_letters = ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J"]
    for row_idx, row_values in enumerate(rows, start=1):
        cells = []
        for col_idx, cell_val in enumerate(row_values):
            col_letter = col_letters[col_idx] if col_idx < len(col_letters) else "Z"
            cell_ref = f"{col_letter}{row_idx}"
            if isinstance(cell_val, (int, float)):
                cells.append(f'<c r="{cell_ref}"><v>{cell_val}</v></c>')
            else:
                clean_str = str(cell_val).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                cells.append(f'<c r="{cell_ref}" t="inlineStr"><is><t>{clean_str}</t></is></c>')
        row_str = f'<row r="{row_idx}">{"".join(cells)}</row>'
        sheet_data_rows.append(row_str)

    sheet_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
  <sheetData>
    {"".join(sheet_data_rows)}
  </sheetData>
</worksheet>"""

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/_rels/workbook.xml.rels", wb_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/worksheets/sheet1.xml", sheet_xml)
    print(f"[+] Created Excel Spreadsheet: {file_path}")


def create_pptx(file_path: str, title: str, subtitle: str, slides_content: list):
    """Generates a valid OpenXML .pptx presentation using standard library zipfile."""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>
  <Override PartName="/ppt/slides/slide1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>
</Types>"""

    root_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>
</Relationships>"""

    ppt_rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide1.xml"/>
</Relationships>"""

    presentation_xml = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:presentation xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
  <p:sldIdLst>
    <p:sldId id="256" r:id="rId1"/>
  </p:sldIdLst>
  <p:sldSz cx="12192000" cy="6858000"/>
</p:presentation>"""

    bullets_xml = []
    for bullet in slides_content:
        clean_b = bullet.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        bullets_xml.append(f"""<a:p>
          <a:pPr lvl="0"/>
          <a:r><a:rPr lang="en-US" sz="1800"/><a:t>{clean_b}</a:t></a:r>
        </a:p>""")

    slide1_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld>
    <p:spTree>
      <p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>
      <p:grpSpPr/>
      <!-- Title Box -->
      <p:sp>
        <p:nvSpPr><p:cNvPr id="2" name="Title"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="838200" y="609600"/><a:ext cx="10515600" cy="1143000"/></a:xfrm></p:spPr>
        <p:txBody>
          <a:bodyPr/>
          <a:p><a:r><a:rPr lang="en-US" b="1" sz="3600"/><a:t>{title}</a:t></a:r></a:p>
          <a:p><a:r><a:rPr lang="en-US" i="1" sz="2000"/><a:t>{subtitle}</a:t></a:r></a:p>
        </p:txBody>
      </p:sp>
      <!-- Content Box -->
      <p:sp>
        <p:nvSpPr><p:cNvPr id="3" name="Content"/><p:cNvSpPr><a:spLocks noGrp="1"/></p:cNvSpPr><p:nvPr/></p:nvSpPr>
        <p:spPr><a:xfrm><a:off x="838200" y="2057400"/><a:ext cx="10515600" cy="4191000"/></a:xfrm></p:spPr>
        <p:txBody>
          <a:bodyPr/>
          {"".join(bullets_xml)}
        </p:txBody>
      </p:sp>
    </p:spTree>
  </p:cSld>
</p:sld>"""

    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with zipfile.ZipFile(file_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("ppt/_rels/presentation.xml.rels", ppt_rels)
        zf.writestr("ppt/presentation.xml", presentation_xml)
        zf.writestr("ppt/slides/slide1.xml", slide1_xml)
    print(f"[+] Created PowerPoint Deck: {file_path}")


def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))

    # 1. Approval Note (.docx)
    create_docx(
        file_path=os.path.join(base_dir, "01_approval_notes", "IOCL_Refinery_Pump_Overhaul_Note.docx"),
        title="INDIAN OIL CORPORATION LIMITED",
        subtitle="NOTE FOR APPROVAL (NFA) - GUWAHATI REFINERY (HCU-11)",
        paragraphs=[
            "Ref No: GHR/MECH/ROT-EQUIP/2026/NFA-0842 | Date: 12-Sep-2026",
            "Classification: RESTRICTED // INTERNAL OPERATIONAL USE ONLY",
            "## 1. Subject & Problem Statement",
            "Proposal for Emergency Overhaul and OEM Spares Procurement for High-Pressure Feed Pump 11-P-101A.",
            "Excessive drive-end bearing vibration recorded at 8.4 mm/s RMS (ISO 10816-3 trip limit: 7.1 mm/s).",
            "Standby pump 11-P-101B running on single-point failure exposure. Loss of throughput risks ₹1.45 Cr/day flaring loss.",
            "## 2. Procurement & CVC Guidelines Compliance",
            "Procurement method: Single Tender on Proprietary Article Certificate (PAC No. PAC/GHR/2026/041) on OEM M/s Sulzer Pumps India.",
            "Compliance verified under IOCL Purchase Manual Section 4.3.2 and CVC Office Order 23/07/07.",
            "## 3. Financial Implications & Budget Availability",
            "Rotor Shaft Assembly (Super Duplex UNS S32750): ₹42,50,000",
            "Dual Cartridge Mechanical Seals (Plan 53B API 682): ₹22,40,000",
            "PEEK Bushing and Wear Rings Set: ₹8,80,000",
            "OEM Supervisory Overhaul & Dynamic Balancing: ₹6,50,000",
            "Total Commitment: INR 94,63,600/- (inclusive of 18% GST).",
            "Budget Head: Emergency Plant Maintenance (GL 520104, Cost Center 4420-1100).",
            "## 4. Recommendation",
            "Approval requested from Executive Director & Head of Refinery (ED & HR) under DOP Item 7.2.1."
        ]
    )

    # 2. Board Presentation (.pptx)
    create_pptx(
        file_path=os.path.join(base_dir, "02_board_presentations", "Q3_Refinery_Modernization_Deck.pptx"),
        title="Project Urja-Vikas: Refinery Modernization & Green Hydrogen",
        subtitle="442nd Board of Directors Meeting - Agenda Item 14",
        slides_content=[
            "Strategic Capex: ₹14,250 Crores allocated across Mumbai & Bina Refineries (FY26-FY29).",
            "Crude Capacity Expansion: Increasing combined throughput from 27.5 MMTPA to 33.0 MMTPA.",
            "Green Hydrogen: 20 KTA PEM Electrolyzer displacing 18% of grey hydrogen (1.85 MMT CO2e/yr avoided).",
            "Capital Structure: 65% Internal Accruals + 35% Multilateral Green Bonds (sub-6.2% coupon).",
            "Projected Return: Weighted Average Internal Rate of Return (IRR) of 17.6%.",
            "Air-Gapped Sovereign AI: On-premises LLM workbench ensuring 100% data residency and zero cloud leaks."
        ]
    )

    # 3. Engineering Calculations (.xlsx)
    calc_rows = [
        ["ASME BOILER & PRESSURE VESSEL CODE (SECTION VIII DIV 1) - WALL THICKNESS CALCULATION"],
        ["Equipment Tag", "11-V-102", "Service", "Hydrocracker HP Separator"],
        ["Material", "SA-387 Gr 22 Cl 2", "Code", "ASME BPVC Sec VIII Div 1 (2023)"],
        [],
        ["DESIGN PARAMETER", "SYMBOL", "VALUE", "UNITS", "CODE REFERENCE"],
        ["Internal Design Pressure", "P", 14.50, "MPa (145.0 barg)", "Process Datasheet"],
        ["Design Temperature", "T", 285.0, "deg C", "Process Datasheet"],
        ["Inside Shell Diameter", "Di", 2400.0, "mm", "Equipment Sizing"],
        ["Inside Shell Radius", "R", 1200.0, "mm", "Di / 2"],
        ["Allowable Stress @ 285C", "S", 138.0, "MPa", "ASME Sec II Part D Table 1A"],
        ["Joint Efficiency (100% RT)", "E", 1.00, "-", "ASME UW-11(a) Type 1 Butt Weld"],
        ["Corrosion Allowance", "CA", 4.0, "mm", "Owner Specification"],
        [],
        ["CALCULATION RESULTS", "FORMULA", "VALUE", "UNITS", "COMPLIANCE STATUS"],
        ["Cylindrical Shell Req Thickness", "t = (P*R)/(S*E - 0.6*P) + CA", 138.57, "mm", "MINIMUM CODE REQUIREMENT"],
        ["Selected Nominal Shell Thickness", "t_nom", 145.00, "mm", "PASS (+6.43 mm safety margin)"],
        ["2:1 Ellipsoidal Head Req Thickness", "t = (P*Di)/(2*S*E - 0.2*P) + CA", 131.43, "mm", "MINIMUM CODE REQUIREMENT"],
        ["Selected Nominal Head Thickness", "t_nom_head", 140.00, "mm", "PASS (+8.57 mm safety margin)"],
        ["Maximum Allowable Working Pressure", "MAWP = (S*E*t)/(R + 0.6*t)", 15.15, "MPa (151.5 barg)", "PASS (MAWP > P_design)"],
        ["Hydrostatic Test Pressure", "P_test = 1.3 * MAWP * (S_amb/S_des)", 21.12, "MPa (211.2 barg)", "ASME UG-99(b) Mandatory Test"]
    ]
    create_xlsx(
        file_path=os.path.join(base_dir, "03_engineering_calculations", "ASME_Pressure_Vessel_Thickness_Calc.xlsx"),
        sheet_name="ASME_UG27_Calc",
        rows=calc_rows
    )

    # 4. NDT Ultrasonic Inspection Report (.docx)
    create_docx(
        file_path=os.path.join(base_dir, "06_inspection_reports", "hydrocracker_reactor_ndt_ultrasonic_report.docx"),
        title="STATUTORY ULTRASONIC THICKNESS SURVEY REPORT",
        subtitle="NON-DESTRUCTIVE TESTING LABORATORY - API 510 / ASME SECTION V",
        paragraphs=[
            "Report No: NDT/HCU/2026/UT-9021 | Date: 04-Sep-2026",
            "Unit: Hydrocracker (HCU-11) | Equipment: HP Separator (11-V-102)",
            "Base Metal: SA-387 Gr 22 Cl 2 (2.25Cr-1Mo) | Nominal Thickness: 145.0 mm | Code Min (t_min): 138.57 mm",
            "## 1. Ultrasonic C-Scan Grid Readings",
            "Point TH-01 (Top Head Crown): 139.60 mm (Loss: 0.60 mm, Rate: 0.05 mm/yr) - ACCEPTABLE",
            "Point SC-1A (Shell C-1 0 deg N): 142.40 mm (Loss: 2.70 mm, Rate: 0.20 mm/yr) - ACCEPTABLE",
            "Point SC-2A (Shell C-2 90 deg E): 141.20 mm (Loss: 4.00 mm, Rate: 0.325 mm/yr) - MONITOR",
            "Point BK-01 (Bottom Knuckle Impingement): 138.20 mm (Loss: 6.80 mm, Rate: 0.75 mm/yr) - CRITICAL BREACH",
            "## 2. Defect Finding & Remaining Life",
            "Point BK-01 measured thickness (138.20 mm) has BREACHED code minimum allowable (138.57 mm) by -0.37 mm.",
            "Remaining service life per API 510 Section 7.1.1 is -0.49 Years (EXPIRED).",
            "HTHA micro-fissuring indications detected on longitudinal weld seam L-1.",
            "## 3. Statutory Disposition & Mandatory Action",
            "1. IMMEDIATE DERATING: Operating pressure derated from 145 barg to 118 barg.",
            "2. EMERGENCY APPROVAL NOTE: Initiate Note for Approval for 347 SS weld overlay restoration (Estimated: ₹88 Lakhs)."
        ]
    )
    print("\n[SUCCESS] All 4 native OpenXML documents generated successfully!")


if __name__ == "__main__":
    main()
