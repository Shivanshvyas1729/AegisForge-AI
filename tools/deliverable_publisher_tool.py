"""
AegisForge-AI — Sovereign Deliverable Publisher Tool
=====================================================
Compiles AI-generated Markdown narratives into certified, executive-ready
corporate deliverables (.docx & .pdf) using pypandoc with cryptographic
SHA-256 audit ledger seals.

Pipeline Architecture:
  LLM / Multi-Agent Narrative ➔ Markdown File (.md) ➔ pypandoc (DOCX & PDF) ➔ SHA-256 Audit Seal

Key Tenets:
  - Zero hardcoding: completely dynamic Markdown-driven compilation
  - Native pypandoc conversion: robust, industry-standard, no brittle custom XML
  - Triple deliverable outputs: raw .md source, editable .docx, and certified .pdf
  - SQLite Cryptographic AuditLedger commit for tamper evidence
  - 100% backward compatibility for legacy positional arguments
"""

from __future__ import annotations

import os
import re
import json
import hashlib
import datetime
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

OUTPUT_DIR = PROJECT_ROOT / "data" / "output"

import logging
logger = logging.getLogger("AegisForge.DeliverablePublisher")

try:
    import pypandoc
except ImportError:
    pypandoc = None

try:
    from xhtml2pdf import pisa
except ImportError:
    pisa = None

from langchain_core.tools import tool


def _safe_filename(base_name: str) -> str:
    """Sanitize strings into safe file system names."""
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_", "."} else "_" for ch in base_name)
    return cleaned.strip("._") or "Approval_Note"


def _build_styled_pdf_html(html_body: str, title: str = "Corporate Engineering Deliverable") -> str:
    """Wrap pandoc-generated HTML into an executive corporate PSU styling template."""
    # Sanitize emojis / high unicode chars that Helvetica cannot render in PDF
    clean_body = re.sub(r'[\U00010000-\U0010ffff]', '', html_body)
    clean_body = clean_body.replace('Δ', 'Delta')
    return f"""<!DOCTYPE html>


<html>
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
@page {{
    size: a4 portrait;
    margin: 18mm 16mm 20mm 16mm;
    @bottom-right {{
        content: "Page " counter(page) " of " counter(pages);
        font-size: 8pt;
        color: #64748b;
    }}
}}
body {{
    font-family: Helvetica, Arial, sans-serif;
    font-size: 9.5pt;
    line-height: 1.5;
    color: #1e293b;
}}
h1 {{
    color: #0f172a;
    font-size: 16pt;
    font-weight: bold;
    border-bottom: 2px solid #2563eb;
    padding-bottom: 5px;
    margin-top: 5px;
    margin-bottom: 12px;
    text-transform: uppercase;
    letter-spacing: 0.03em;
}}
h2 {{
    color: #1e3a8a;
    font-size: 12pt;
    font-weight: bold;
    margin-top: 14px;
    margin-bottom: 6px;
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 2px;
}}
h3 {{
    color: #334155;
    font-size: 10.5pt;
    font-weight: bold;
    margin-top: 10px;
    margin-bottom: 4px;
}}
p {{
    margin-top: 4px;
    margin-bottom: 6px;
}}
table {{
    width: 100%;
    border-collapse: collapse;
    margin: 10px 0 14px 0;
}}
th, td {{
    border: 1px solid #cbd5e1;
    padding: 5px 8px;
    text-align: left;
    font-size: 8.5pt;
}}
th {{
    background-color: #0f172a;
    color: #ffffff;
    font-weight: bold;
}}
tr:nth-child(even) td {{
    background-color: #f8fafc;
}}
blockquote {{
    background-color: #eff6ff;
    border-left: 4px solid #2563eb;
    padding: 8px 12px;
    margin: 10px 0;
    color: #1e3a8a;
    font-size: 9pt;
}}
hr {{
    border: 0;
    border-top: 1px solid #cbd5e1;
    margin: 12px 0;
}}
code {{
    font-family: Courier, monospace;
    background-color: #f1f5f9;
    padding: 1px 4px;
    font-size: 8.5pt;
    color: #0f172a;
}}
ul, ol {{
    margin-top: 4px;
    margin-bottom: 8px;
    padding-left: 20px;
}}
li {{
    margin-bottom: 3px;
}}
.audit-seal-box {{
    margin-top: 18px;
    border: 1px solid #22c55e;
    background-color: #f0fdf4;
    padding: 8px 12px;
    font-family: Courier, monospace;
    font-size: 8pt;
    color: #166534;
}}
</style>
</head>
<body>
{clean_body}
</body>
</html>"""


def publish_deliverable(
    *args,
    markdown_content: Optional[str] = None,
    equipment_id: Optional[str] = None,
    structured_metrics: Optional[Dict[str, Any]] = None,
    human_sign_off: Optional[Dict[str, Any]] = None,
    output_filename: Optional[str] = None,
    generate_docx: bool = True,
    generate_pdf: bool = True,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Core publishing function:
      1. Writes dynamic AI Markdown to .md file.
      2. Uses pypandoc to generate .docx.
      3. Uses pypandoc + xhtml2pdf to generate .pdf.
      4. Calculates SHA-256 seal and records in cryptographic audit ledger.
    """
    try:
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

        content_md = markdown_content or ""
        metrics = dict(structured_metrics or {})
        sign_off = dict(human_sign_off or {})
        eq_id = equipment_id or ""

        # -------------------------------------------------------------------
        # Backward-Compatible Adaptor for Legacy Positional Calls:
        # deliverable_publisher_tool(insp, calc, comp, summ)
        # -------------------------------------------------------------------
        if len(args) >= 1 and isinstance(args[0], dict):
            insp = args[0]
            calc = args[1] if len(args) > 1 and isinstance(args[1], dict) else {}
            comp = args[2] if len(args) > 2 and isinstance(args[2], dict) else {}
            summ = args[3] if len(args) > 3 and isinstance(args[3], str) else ""

            eq_id = eq_id or str(insp.get("equipment_id") or calc.get("equipment_id") or "Asset")
            metrics.update(calc)
            if comp:
                metrics["compliance"] = comp

            legacy_md_parts = []
            if summ:
                legacy_md_parts.append(f"## Executive Summary\n{summ}\n")
            if insp:
                legacy_md_parts.append("## Inspection & Asset Specification")
                for k, v in insp.items():
                    legacy_md_parts.append(f"- **{k.replace('_', ' ').title()}:** {v}")
                legacy_md_parts.append("")
            if calc:
                legacy_md_parts.append("## Engineering Stress Calculation Analysis")
                for k, v in calc.items():
                    legacy_md_parts.append(f"- **{k.replace('_', ' ').title()}:** {v}")
                legacy_md_parts.append("")
            if comp:
                legacy_md_parts.append("## Statutory Procurement & Vigilance Audit")
                for k, v in comp.items():
                    legacy_md_parts.append(f"- **{k.replace('_', ' ').title()}:** {v}")
                legacy_md_parts.append("")

            content_md = "\n".join(legacy_md_parts)

        # Infer equipment ID dynamically if missing
        if not eq_id:
            m_eq = re.search(r'\b(\d{1,3}-[A-Z]{1,3}-\d{2,4})\b', content_md)
            if m_eq:
                eq_id = m_eq.group(1)
            else:
                eq_id = metrics.get("equipment_id") or "Asset"

        # Dynamically append Human Sign-Off block if present and not already formatted
        if sign_off and "Competent Authority Sign-Off" not in content_md:
            approved_str = "APPROVED / AUTHORIZED" if sign_off.get("approved") else "REJECTED / CONDITIONAL"
            feedback_str = sign_off.get("feedback") or "Verified and authorized by Competent Authority."
            content_md += (
                f"\n\n---\n\n"
                f"## Competent Authority Operational Sign-Off\n\n"
                f"| Attribute | Human-in-the-Loop Verdict |\n"
                f"| :--- | :--- |\n"
                f"| **Authority Status** | **{approved_str}** |\n"
                f"| **Authority Role** | {sign_off.get('authority', 'Chief Plant Engineer / Competent Authority')} |\n"
                f"| **Operational Directives** | {feedback_str} |\n"
                f"| **Authorization Timestamp** | {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST |\n"
            )

        # Base file name
        base_name = output_filename or f"{_safe_filename(eq_id)}_Approval_Note"
        base_name = _safe_filename(base_name)

        md_path   = OUTPUT_DIR / f"{base_name}.md"
        docx_path = OUTPUT_DIR / f"{base_name}.docx"
        pdf_path  = OUTPUT_DIR / f"{base_name}.pdf"

        # -------------------------------------------------------------------
        # STEP 1: SAVE DYNAMIC AI MARKDOWN FILE
        # -------------------------------------------------------------------
        with open(md_path, "w", encoding="utf-8") as f_md:
            f_md.write(content_md.strip() + "\n")
        logger.info(f"Published dynamic Markdown file: {md_path}")

        # Compute canonical hash of the source Markdown
        integrity_hash = hashlib.sha256(content_md.strip().encode("utf-8")).hexdigest()

        # Append SHA-256 seal section to Markdown if not already present
        if "CRYPTOGRAPHIC AUDIT LEDGER SEAL" not in content_md:
            seal_block = (
                f"\n\n---\n\n"
                f"> **[SEAL] CRYPTOGRAPHIC AUDIT LEDGER SEAL**  \n"
                f"> **SHA-256 Hash:** `{integrity_hash}`  \n"
                f"> **Classification:** INTERNAL / PSU STATUTORY DELIVERABLE  \n"
                f"> **Timestamp:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST | Status: CERTIFIED_TAMPER_EVIDENT\n"

            )
            with open(md_path, "a", encoding="utf-8") as f_md:
                f_md.write(seal_block)
            content_md += seal_block

        # -------------------------------------------------------------------
        # STEP 2: CONVERT MARKDOWN TO DOCX VIA PYPANDOC (IF NEEDED)
        # -------------------------------------------------------------------
        has_docx = False
        if generate_docx:
            try:
                if pypandoc is not None:
                    pypandoc.convert_file(
                        str(md_path),
                        "docx",
                        format="md",
                        outputfile=str(docx_path)
                    )
                    has_docx = docx_path.exists()
                else:
                    # Fallback to python-docx if pypandoc missing
                    from docx import Document
                    doc = Document()
                    doc.add_heading(f"Engineering Deliverable — {eq_id}", level=0)
                    for line in content_md.splitlines():
                        if line.startswith("# "):
                            doc.add_heading(line[2:], level=1)
                        elif line.startswith("## "):
                            doc.add_heading(line[3:], level=2)
                        elif line.startswith("### "):
                            doc.add_heading(line[4:], level=3)
                        else:
                            doc.add_paragraph(line)
                    doc.save(str(docx_path))
                    has_docx = docx_path.exists()
            except Exception as docx_err:
                logger.error(f"Failed to compile DOCX via pypandoc: {docx_err}")
                has_docx = False

        # -------------------------------------------------------------------
        # STEP 3: CONVERT MARKDOWN TO PDF VIA PYPANDOC + XHTML2PDF
        # -------------------------------------------------------------------
        has_pdf = False
        if generate_pdf:
            try:
                if pypandoc is not None and pisa is not None:
                    html_body = pypandoc.convert_file(str(md_path), "html", format="md")
                    styled_html = _build_styled_pdf_html(html_body, title=f"AegisForge Deliverable — {eq_id}")
                    with open(pdf_path, "wb") as f_pdf:
                        pisa_status = pisa.CreatePDF(styled_html, dest=f_pdf)
                    has_pdf = pdf_path.exists() and (pisa_status.err == 0)
                else:
                    logger.warning("pypandoc or xhtml2pdf not available for PDF generation.")
            except Exception as pdf_err:
                logger.error(f"Failed to compile PDF: {pdf_err}")
                has_pdf = False

        # -------------------------------------------------------------------
        # STEP 4: DIRECT COMMIT TO SQLITE CRYPTOGRAPHIC AUDIT LEDGER
        # -------------------------------------------------------------------
        try:
            from tools.audit_trail import AuditLedger
            ledger = AuditLedger()
            ledger.append_event(
                event_type="DELIVERABLE_PUBLISHED",
                workflow_id=eq_id,
                tool_name="deliverable_publisher_tool",
                caller="deliverable_publisher",
                agent_version="2.1.0",
                tool_version="2.1.0",
                inputs={"equipment_id": eq_id, "md_path": str(md_path)},
                outputs={
                    "sha256_seal": integrity_hash,
                    "md_path": str(md_path),
                    "docx_path": str(docx_path) if has_docx else None,
                    "pdf_path": str(pdf_path) if has_pdf else None,
                },
                status="CERTIFIED_TAMPER_EVIDENT",
            )
        except Exception as ledger_err:
            logger.warning(f"Audit ledger logging skipped or busy: {ledger_err}")

        # Compute relative paths for clean representation
        def _rel(p: Path) -> str:
            try:
                return p.relative_to(PROJECT_ROOT).as_posix()
            except ValueError:
                return str(p)

        res: Dict[str, Any] = {
            "status": "SUCCESS",
            "equipment_id": eq_id,
            "md_path": _rel(md_path),
            "sha256_hash": integrity_hash,
            "preview_markdown": content_md,
        }
        if has_docx:
            res["docx_path"] = _rel(docx_path)
        if has_pdf:
            res["pdf_path"] = _rel(pdf_path)

        return res

    except Exception as exc:
        logger.error(f"Deliverable publisher error: {exc}", exc_info=True)
        return {"status": "ERROR", "message": str(exc)}


@tool
def deliverable_publisher_tool(
    markdown_content: Optional[str] = None,
    equipment_id: Optional[str] = None,
    output_filename: Optional[str] = None,
    generate_docx: bool = True,
    generate_pdf: bool = True,
    **kwargs: Any
) -> Dict[str, Any]:
    """
    Generates official corporate deliverable files (.md, .docx, .pdf) from AI Markdown.
    Uses pypandoc for document compilation and records a cryptographic SHA-256 seal in the audit ledger.
    """
    return publish_deliverable(
        markdown_content=markdown_content,
        equipment_id=equipment_id,
        output_filename=output_filename,
        generate_docx=generate_docx,
        generate_pdf=generate_pdf,
        **kwargs
    )


if __name__ == "__main__":
    sample_text = """# MANGALORE REFINERY & PETROCHEMICALS LTD
**Document:** Statutory Notes for Approval (NFA)
**Vessel Tag:** 11-V-102
**Date:** 2026-09-29

## 1. Executive Summary
Inspection of High-Pressure Separator 11-V-102 revealed localized thinning. Calculations performed under ASME Section VIII UG-27.

| Parameter | Required | Actual | Verdict |
| :--- | :--- | :--- | :--- |
| Thickness | 138.57 mm | 138.20 mm | Deficit (-0.37 mm) |
| Derated MAWP | 14.50 MPa | 14.46 MPa | Derated Safe |
"""
    result = deliverable_publisher_tool.invoke({
        "markdown_content": sample_text,
        "equipment_id": "11-V-102",
        "output_filename": "11-V-102_Pypandoc_Test"
    })
    print("Result:", json.dumps(result, indent=2))
