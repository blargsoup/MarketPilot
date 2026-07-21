"""
Market data service.
"""

import pandas as pd

from .yahoo_data_provider import YahooDataProvider


class MarketDataService:
    """
    Main interface for obtaining market data.
    """

    def __init__(self):

        self.provider = YahooDataProvider()

    def get_history(
        self,
        symbol: str,
        period: str = "5y",
        interval: str = "1d",
    ) -> pd.DataFrame:

        return self.provider.get_history(
            symbol,
            period=period,
            interval=interval,
        )