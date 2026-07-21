"""
Yahoo Finance implementation.
"""

import logging

import pandas as pd
import yfinance as yf

from .provider import MarketDataProvider


class YahooDataProvider(MarketDataProvider):
    """Downloads historical market data from Yahoo Finance."""

    def __init__(self):

        self.logger = logging.getLogger("MarketPilot")

    def get_history(
        self,
        symbol: str,
        period: str = "5y",
        interval: str = "1d",
    ) -> pd.DataFrame:

        self.logger.info("Downloading %s...", symbol)

        df = yf.download(
            symbol,
            period=period,
            interval=interval,
            auto_adjust=True,
            progress=False,
        )

        # Flatten MultiIndex columns for single ticker downloads.
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)

        if df.empty:
            raise RuntimeError(f"No data returned for {symbol}")

        if not df.index.is_monotonic_increasing:
            raise RuntimeError(f"{symbol} returned unsorted data")

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        ]

        for column in required_columns:

            if column not in df.columns:

                raise RuntimeError(
                    f"{symbol} missing required column '{column}'"
                )

        self.logger.info(
            "%s downloaded successfully (%d rows)",
            symbol,
            len(df),
        )

        return df