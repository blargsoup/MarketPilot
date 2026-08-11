"""
Market data service.
"""

from typing import Dict

from marketpilot.cache import CacheManager
from marketpilot.models import MarketHistory

from .yahoo_data_provider import YahooDataProvider
from .treasury_bill_provider import TreasuryBillProvider
from concurrent.futures import ThreadPoolExecutor, as_completed


class MarketDataService:
    """
    Main interface for obtaining market data.
    """

    def __init__(self):

        self.provider = YahooDataProvider()

        self.providers = {
            "TBILL": TreasuryBillProvider(),
        }

        self.cache = CacheManager()

    def get_history(
        self,
        symbol,
        period="max",
        interval="1d",
        refresh=True,
    ) -> MarketHistory:

        if symbol == "TBILL" and self.cache.exists(symbol):

            if not refresh:

                return MarketHistory(
                    symbol=symbol,
                    data=self.cache.load(symbol),
                )

            #
            # FRED is small enough that refreshing the complete
            # historical series is acceptable.
            #

            provider = self._provider_for(symbol)

            df = provider.get_history(
                symbol,
                period="max",
                interval=interval,
            )

            self.cache.save(
                symbol,
                df,
            )

            return MarketHistory(
                symbol=symbol,
                data=df,
            )

        #
        # Existing cache
        #

        if self.cache.exists(symbol):

            if not refresh:

                return MarketHistory(
                    symbol=symbol,
                    data=self.cache.load(symbol),
                )

            print(f"Updating {symbol} cache...")

            cached = self.cache.load(symbol)

            #
            # Only fetch recent history
            #

            provider = self._provider_for(
                symbol
            )

            latest = provider.get_history(
                symbol,
                period="10d",
                interval=interval,
            )

            #
            # Merge
            #

            df = (
                cached.combine_first(latest)
                .combine_first(cached)
            )

            #
            # Overwrite cached rows with Yahoo's newest copy
            #

            df.update(latest)

            #
            # Sort
            #

            df = df.sort_index()

            #
            # Remove duplicates
            #

            df = df[
                ~df.index.duplicated(keep="last")
            ]

            #
            # Save refreshed cache
            #

            self.cache.save(symbol, df)

            return MarketHistory(
                symbol=symbol,
                data=df,
            )

        #
        # First download
        #

        print(f"Creating cache for {symbol}...")

        provider = self._provider_for(
            symbol
        )

        df = provider.get_history(
            symbol,
            period="max",
            interval=interval,
        )

        self.cache.save(symbol, df)

        return MarketHistory(
            symbol=symbol,
            data=df,
        )

    def _provider_for(
        self,
        symbol: str,
    ):
        return self.providers.get(
            symbol,
            self.provider,
        )

    def get_histories(
        self,
        symbols: list[str],
        period: str = "max",
        interval: str = "1d",
        refresh: bool = True,
    ) -> Dict[str, MarketHistory]:

        market = {}

        with ThreadPoolExecutor(max_workers=8) as executor:

            futures = {
                executor.submit(
                    self.get_history,
                    symbol,
                    period,
                    interval,
                    refresh,
                ): symbol
                for symbol in symbols
            }

            for future in as_completed(futures):

                symbol = futures[future]
                market[symbol] = future.result()

        return market