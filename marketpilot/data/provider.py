"""
Base class for market data providers.
"""

from abc import ABC, abstractmethod
import pandas as pd


class MarketDataProvider(ABC):
    """Abstract market data provider."""

    @abstractmethod
    def get_history(
        self,
        symbol: str,
        period: str = "5y",
        interval: str = "1d",
    ) -> pd.DataFrame:
        """Return historical price data."""