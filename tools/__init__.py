"""
tools package — Sovereign Industrial AI Engineering & Compliance Toolset.
Exports standardized LangChain tool interfaces (*_tool) alongside underlying
core pure-Python functions for direct programmatic invocation.
"""

# Core Engineering & Math Engines
from .ug27_core import (
    validate_ug27_parameters,
    calculate_t_req,
    calculate_delta_margin,
    calculate_remaining_life,
    calculate_derated_mawp_bar,
)
from .asme_calculator import evaluate_vessel_integrity, asme_calc_tool
from .thickness_grid_analyzer import analyze_thickness_grid, thickness_grid_tool

# Security, Sandbox & Network Telemetry
from .sandbox import execute_python_code, sandbox_tool
from .network_verifier import audit_network_isolation, verify_network_tool

# Compliance & Statutory Auditing
from .compliance_auditor import audit_procurement_compliance, cvc_audit_tool

# Multimodal Ingestion & Parameter Extraction
from .inspection_extractor_tool import extract_inspection_parameters, inspection_extractor_tool

# File I/O & Audit Trail
from .file_io import read_or_write_file, file_io_tool
from .audit_trail import append_audit_event, verify_audit_ledger_integrity
from .routing_guard import supervisor_dispatch_guard, execute_human_override

# Knowledge Retrieval
from .rag import search_local_knowledge, rag_tool

# Document Generation & Deliverable Publishing
try:
    from .doc_generator import (
        generate_deliverable_tool,
        generate_both_deliverables,
        generate_docx_deliverable,
        generate_pdf_deliverable,
        compile_nfa_documents_for_ui,
    )
except ImportError:
    generate_deliverable_tool = None
    generate_both_deliverables = None
    generate_docx_deliverable = None
    generate_pdf_deliverable = None
    compile_nfa_documents_for_ui = None

__all__ = [
    # 9 Canonical Agent Tools (Uniform *_tool convention)
    "rag_tool",
    "sandbox_tool",
    "asme_calc_tool",
    "thickness_grid_tool",
    "inspection_extractor_tool",
    "cvc_audit_tool",
    "file_io_tool",
    "generate_deliverable_tool",
    "verify_network_tool",
    # Core Mathematical & Assessment Functions
    "validate_ug27_parameters",
    "calculate_t_req",
    "calculate_delta_margin",
    "calculate_remaining_life",
    "calculate_derated_mawp_bar",
    "evaluate_vessel_integrity",
    "analyze_thickness_grid",
    "execute_python_code",
    "audit_network_isolation",
    "audit_procurement_compliance",
    "extract_inspection_parameters",
    "read_or_write_file",
    "search_local_knowledge",
    "generate_both_deliverables",
    "generate_docx_deliverable",
    "generate_pdf_deliverable",
    "compile_nfa_documents_for_ui",
    "append_audit_event",
    "verify_audit_ledger_integrity",
    "supervisor_dispatch_guard",
    "execute_human_override",
]
