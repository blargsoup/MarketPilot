"""
Base strategy interface.
"""

from abc import ABC, abstractmethod

from .state import PortfolioState


class Strategy(ABC):

    name = "Unnamed Strategy"
    initial_state = PortfolioState.TQQQ

    @abstractmethod
    def evaluate(
        self,
        current_state,
        signals,
    ):
        """
        Return a StrategyResult.
        """
        pass
