"""
MarketPilot indicator library.

All strategies obtain technical indicators through the
IndicatorEngine instead of calculating them directly.
"""

from .engine import IndicatorEngine

__all__ = [
    "IndicatorEngine",
]