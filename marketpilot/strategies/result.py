"""
Result returned by a strategy evaluation.
"""

from dataclasses import dataclass

from .state import PortfolioState


@dataclass
class StrategyResult:

    current_state: PortfolioState

    new_state: PortfolioState

    changed: bool

    reasons: list[str]