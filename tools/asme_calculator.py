"""
Compatibility Layer: asme_calculator -> mining_math_core
=========================================================
Pivoted to AegisForge-Mining for CMPDI / Coal India Limited.
Re-exports MiningMathCore, calculate_stripping_ratio, and calculate_coal_reserves.
"""

from tools.mining_math_core import (
    MiningMathCore,
    AsmeCalculator,
    calculate_stripping_ratio,
    calculate_coal_reserves,
    calculate_asme_stresses,
    compute_stripping_ratio_deterministic,
    compute_geological_reserves_deterministic,
)

__all__ = [
    "MiningMathCore",
    "AsmeCalculator",
    "calculate_stripping_ratio",
    "calculate_coal_reserves",
    "calculate_asme_stresses",
    "compute_stripping_ratio_deterministic",
    "compute_geological_reserves_deterministic",
]
