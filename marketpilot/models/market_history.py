"""
Represents historical price data for a single symbol.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass
class MarketHistory:
    """
    Wrapper around a pandas DataFrame containing
    historical market prices.
    """

    symbol: str
    data: pd.DataFrame

    @property
    def rows(self) -> int:
        return len(self.data)

    @property
    def first_date(self):
        return self.data.index[0]

    @property
    def last_date(self):
        return self.data.index[-1]

    @property
    def latest_close(self) -> float:
        return float(self.data["Close"].iloc[-1])

    @property
    def latest_volume(self) -> float:
        return float(self.data["Volume"].iloc[-1])

    @property
    def close(self) -> pd.Series:
        return self.data["Close"]

    @property
    def high(self) -> pd.Series:
        return self.data["High"]

    @property
    def low(self) -> pd.Series:
        return self.data["Low"]

    @property
    def volume(self) -> pd.Series:
        return self.data["Volume"]