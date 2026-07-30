"""
Base strategy interface.
"""

from abc import ABC, abstractmethod

from .state import PortfolioState


class Strategy(ABC):

    name = "Unnamed Strategy"
    initial_state = PortfolioState.AGGRESSIVE
    
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
