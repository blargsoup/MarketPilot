"""
Market data service.
"""

from typing import Dict

from marketpilot.cache import CacheManager
from marketpilot.models import MarketHistory

from .yahoo_data_provider import YahooDataProvider


class MarketDataService:
    """
    Main interface for obtaining market data.
    """

    def __init__(self):

        self.provider = YahooDataProvider()
        self.cache = CacheManager()

    def get_history(
        self,
        symbol: str,
        period: str = "5y",
        interval: str = "1d",
    ) -> MarketHistory:

        # Try cache first
        if self.cache.exists(symbol):

            print(f"Loading {symbol} from cache...")

            df = self.cache.load(symbol)

            return MarketHistory(
                symbol=symbol,
                data=df,
            )

        # Otherwise download
        df = self.provider.get_history(
            symbol,
            period=period,
            interval=interval,
        )

        # Save for next time
        self.cache.save(symbol, df)

        return MarketHistory(
            symbol=symbol,
            data=df,
        )

    def get_histories(
        self,
        symbols: list[str],
        period: str = "5y",
        interval: str = "1d",
    ) -> Dict[str, MarketHistory]:

        market = {}

        for symbol in symbols:

            market[symbol] = self.get_history(
                symbol,
                period,
                interval,
            )

        return market