"""
Complete analysis result.

Represents one snapshot of the market,
signals and strategy evaluation.
"""

from dataclasses import dataclass


@dataclass
class AnalysisResult:

    market: dict

    signals: object

    strategy: object

    defensive: object