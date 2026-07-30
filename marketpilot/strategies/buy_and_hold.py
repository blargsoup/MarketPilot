"""Simple buy-and-hold strategy implementations."""

from .base import Strategy
from .result import StrategyResult
from .state import PortfolioState


class BuyAndHoldStrategy(Strategy):
    """Hold one portfolio state for the full backtest period."""

    def __init__(self, state: PortfolioState = PortfolioState.AGGRESSIVE):
        self.initial_state = state
        self.name = f"Buy & Hold {state.asset}"

    def evaluate(
        self,
        current_state: PortfolioState,
        signals,
    ) -> StrategyResult:
        """Keep the original position regardless of market conditions."""

        return StrategyResult(
            current_state=current_state,
            new_state=current_state,
            changed=False,
            reasons=[],
        )
