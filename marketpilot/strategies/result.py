"""
Result returned by a strategy evaluation.
"""

from dataclasses import dataclass


@dataclass
class StrategyResult:

    state: str

    reasons: list[str]