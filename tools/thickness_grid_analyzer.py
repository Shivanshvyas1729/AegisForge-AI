"""
Compatibility Layer: thickness_grid_analyzer -> production_grid_analyzer
========================================================================
Pivoted to AegisForge-Mining for CMPDI / Coal India Limited.
Re-exports ProductionGridAnalyzer, analyze_production_grid, and analyze_thickness_grid.
"""

from tools.production_grid_analyzer import (
    ProductionGridAnalyzer,
    ThicknessGridAnalyzer,
    analyze_production_grid,
    analyze_thickness_grid,
    ProductionInput,
)

__all__ = [
    "ProductionGridAnalyzer",
    "ThicknessGridAnalyzer",
    "analyze_production_grid",
    "analyze_thickness_grid",
    "ProductionInput",
]
