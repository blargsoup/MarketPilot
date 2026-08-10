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

    @property
    def action(self):
        """
        Human-readable description of the portfolio transition.
        """

        if not self.changed:

            return "HOLD"

        return (
            f"{self.current_state.name}"
            f" -> "
            f"{self.new_state.name}"
        )