"""
tools package — Engineering tools for AegisForge-AI.
ASME calculator, sandbox execution, file I/O, local RAG, and document generators.

Note: Imports are wrapped to prevent cascading failures when optional
dependencies (python-docx, reportlab) aren't installed.
"""

from .asme_calculator import evaluate_vessel_integrity
from .sandbox import execute_python_code
from .file_io import read_or_write_file
from .rag import search_local_knowledge

# Document generators need python-docx and reportlab — import gracefully
try:
    from .doc_generator import (
        generate_docx_deliverable,
        generate_pdf_deliverable,
        generate_both_deliverables,
    )
except ImportError:
    generate_docx_deliverable = None
    generate_pdf_deliverable = None
    generate_both_deliverables = None

__all__ = [
    "evaluate_vessel_integrity",
    "execute_python_code",
    "read_or_write_file",
    "search_local_knowledge",
    "generate_docx_deliverable",
    "generate_pdf_deliverable",
    "generate_both_deliverables",
]
