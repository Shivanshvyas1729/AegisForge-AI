"""
Compatibility Layer: inspection_extractor_tool -> geological_extractor_tool
============================================================================
Pivoted to AegisForge-Mining. Re-exports GeologicalExtractorTool and extraction functions.
"""

from tools.geological_extractor_tool import (
    GeologicalExtractorTool,
    InspectionExtractorTool,
    extract_geological_data,
    extract_inspection_data,
    FileInput,
)

__all__ = [
    "GeologicalExtractorTool",
    "InspectionExtractorTool",
    "extract_geological_data",
    "extract_inspection_data",
    "FileInput",
]
