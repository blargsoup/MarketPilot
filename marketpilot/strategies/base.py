"""
Base strategy interface.
"""

from abc import ABC, abstractmethod


class Strategy(ABC):

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