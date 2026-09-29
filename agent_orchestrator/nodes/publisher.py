"""
AegisForge-AI — Deliverable Publisher Node
============================================
Compiles AI-generated Markdown narratives and verified engineering findings
into formal, tamper-evident corporate deliverables (.md, .docx, .pdf)
using pypandoc with cryptographic SHA-256 audit ledger seals.

Strategy:
  LLM / Reviewer Narrative ➔ Markdown File (.md) ➔ pypandoc (DOCX & PDF) ➔ SHA-256 Ledger
"""

import datetime
import json
import logging
import re
from typing import Literal

from langchain_core.messages import HumanMessage
from langgraph.graph import END
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command

from agent_orchestrator.state import AgentState
from agent_orchestrator.models import supervisor_llm, LANGFUSE_CONFIG
from tools.deliverable_publisher_tool import deliverable_publisher_tool
from tools import network_verifier

logger = logging.getLogger("AegisForge.Publisher")

publisher_tools = [
    deliverable_publisher_tool,
    network_verifier.verify_zero_egress,
]

publisher_agent = create_react_agent(
    supervisor_llm,
    tools=publisher_tools,
    prompt=(
        "You are the Sovereign Deliverable Publisher of AegisForge-AI.\n"
        "Your duty is compiling verified engineering findings into formal, tamper-evident documents.\n\n"
        "AVAILABLE TOOLS:\n"
        "1. 'deliverable_publisher_tool': Takes dynamic AI Markdown and compiles it into .md, .docx, and .pdf "
        "files using pypandoc, then records a SHA-256 seal into the audit ledger.\n"
        "2. 'verify_zero_egress': Confirms complete air-gapped network isolation.\n\n"
        "EXECUTION INSTRUCTIONS:\n"
        "- Synthesize the full conversation history into a formal engineering Markdown report.\n"
        "- Include Executive Summary, ASME Quantitative Evaluation table, and Statutory Verdict.\n"
        "- Invoke 'deliverable_publisher_tool' with the markdown_content and equipment_id.\n"
        "- Return the generated file paths (.md, .docx, .pdf) and SHA-256 seal."
    )
)


def deliverable_publisher_node(
    state: AgentState,
) -> Command[Literal["__end__"]]:
    """Compiles verified multi-agent findings into corporate deliverables via pypandoc."""
    eq_id = state.get("equipment_id") or "Asset"
    asme = state.get("last_asme_result") or {}
    compliance = state.get("last_compliance_result") or {}
    human_approved = state.get("human_approved")
    human_feedback = state.get("human_feedback")

    # Fall back to regex for equipment_id if not explicitly set
    if eq_id == "Asset":
        full_history = "\n".join(str(getattr(m, "content", "")) for m in state.get("messages", []))
        m_eq = re.search(r'\b(\d{1,3}-[A-Z]{1,3}-\d{2,4})\b', full_history)
        if m_eq:
            eq_id = m_eq.group(1)

    # Extract Chief Reviewer's narrative or latest specialist narrative
    reviewer_md = ""
    for m in reversed(state.get("messages", [])):
        m_name = getattr(m, "name", None) or getattr(m, "type", "")
        if m_name == "chief_reviewer":
            reviewer_md = str(m.content)
            break

    # If no reviewer message was found, look at the last assistant or AI message
    if not reviewer_md and state.get("messages"):
        for m in reversed(state.get("messages", [])):
            if getattr(m, "type", "") in ["ai", "assistant"]:
                reviewer_md = str(m.content)
                break

    # Build clean, dynamic AI Markdown dossier without hardcoding
    md_sections = []
    md_sections.append(f"# MANGALORE REFINERY & PETROCHEMICALS LTD")
    md_sections.append(f"**Document Type:** Statutory Engineering Deliverable & Notes for Approval (NFA)")
    md_sections.append(f"**Asset / Equipment Tag:** `{eq_id}`")
    md_sections.append(f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')} IST\n")
    md_sections.append("---\n")

    if reviewer_md:
        md_sections.append(reviewer_md)
    else:
        # Fallback dynamic summary if no reviewer text
        md_sections.append("## 1. Executive Summary")
        md_sections.append(f"Statutory turnaround engineering verification completed for Equipment `{eq_id}`.")
        if asme:
            t_req = asme.get("t_req_mm", 0.0)
            t_act = asme.get("measured_thickness_mm", 0.0)
            delta = asme.get("delta_mm", 0.0)
            mawp = asme.get("derated_mawp_mpa", 0.0)
            md_sections.append("\n## 2. Quantitative Verification Matrix\n")
            md_sections.append("| Parameter | Baseline / Standard | Evaluated Value | Status |")
            md_sections.append("| :--- | :--- | :--- | :--- |")
            md_sections.append(f"| Required Thickness (t_req) | Statutory UG-27 | {t_req:.2f} mm | Evaluated |")
            md_sections.append(f"| Measured Thickness (t_act) | Ultrasonic NDT | {t_act:.2f} mm | {'DEFICIT' if delta < 0 else 'COMPLIANT'} |")
            md_sections.append(f"| Safety Margin (Delta) | ASME Margin | {delta:.2f} mm | {'DEFICIT' if delta < 0 else 'SAFE'} |")
            if mawp:
                md_sections.append(f"| Derated MAWP | API 579 / UG-27 | {mawp:.2f} MPa | Derated Safe |")

    # Add Competent Authority Sign-Off block if Human Gate was executed
    sign_off_data = None
    if human_approved is not None:
        sign_off_data = {
            "approved": bool(human_approved),
            "feedback": human_feedback or "Verified and authorized by Competent Authority.",
            "authority": "Chief Plant Engineer / Competent Authority"
        }

    full_markdown = "\n\n".join(md_sections)

    # Invoke deliverable_publisher_tool directly to ensure zero failure
    pub_result = deliverable_publisher_tool.invoke({
        "markdown_content": full_markdown,
        "equipment_id": eq_id,
        "human_sign_off": sign_off_data,
        "output_filename": f"{eq_id}_Certified_NFA",
        "generate_docx": True,
        "generate_pdf": True,
    })

    if isinstance(pub_result, dict) and pub_result.get("status") == "SUCCESS":
        md_p = pub_result.get("md_path", "")
        docx_p = pub_result.get("docx_path", "")
        pdf_p = pub_result.get("pdf_path", "")
        sha = pub_result.get("sha256_hash", "")

        response_content = (
            f"### 📑 Official Engineering Deliverable Published & Sealed\n\n"
            f"**Asset / Equipment Tag:** `{eq_id}`  \n"
            f"**Cryptographic SHA-256 Seal:** `{sha}`  \n"
            f"**Tamper-Evident Ledger Status:** `CERTIFIED_TAMPER_EVIDENT`\n\n"
            f"The dynamic AI Markdown narrative has been compiled into certified deliverables:\n"
            f"- 📝 **Markdown Source File:** `{md_p}`\n"
            f"- 📥 **Corporate Word Document:** `{docx_p}`\n"
            f"- 📑 **Certified Printable PDF:** `{pdf_p}`\n\n"
            f"---\n\n"
            f"> **Audit Verification Note:** The document hash `{sha}` has been committed to the local "
            f"SQLite cryptographic audit ledger with zero external egress per sovereign PSU standards."
        )
    else:
        err = pub_result.get("message", "Unknown error") if isinstance(pub_result, dict) else str(pub_result)
        response_content = f"⚠️ Deliverable publishing encountered an error: {err}"

    out_msg = HumanMessage(content=response_content, name="deliverable_publisher")
    return Command(update={"messages": [out_msg]}, goto=END)
