"""
Simple Buy & Hold strategy.

Uses the StrategyProfile so the exact ETF being held is determined
by the selected market profile.
"""

from .base import Strategy
from .profile import NASDAQ_PROFILE
from .result import StrategyResult
from .state import PortfolioState


class BuyAndHoldStrategy(Strategy):
    """
    Hold the aggressive asset for an entire backtest.
    """

    def __init__(

        self,

        profile=NASDAQ_PROFILE,

    ):

        self.profile = profile

        self.initial_state = PortfolioState.AGGRESSIVE

        self.name = f"Buy & Hold ({profile.name})"

    def evaluate(

        self,

        current_state,

        signals,

    ):

        return StrategyResult(

            current_state=current_state,

            new_state=current_state,

            changed=False,

            reasons=[],

        )