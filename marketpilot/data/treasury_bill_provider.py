"""
Synthetic 3-month Treasury bill cash-equivalent history.

Uses FRED DTB3, the 3-month U.S. Treasury bill secondary-market
rate quoted on a discount basis.

The resulting synthetic price series behaves like a continuously
compounded cash position and is returned in the same OHLCV structure
used by Yahoo market data.
"""

import logging
from io import StringIO
from urllib.request import urlopen

import pandas as pd

from .provider import MarketDataProvider


class TreasuryBillProvider(MarketDataProvider):

    FRED_URL = (
        "https://fred.stlouisfed.org/graph/fredgraph.csv"
        "?id=DTB3"
    )

    def __init__(self):

        self.logger = logging.getLogger("MarketPilot")

    def get_history(
        self,
        symbol: str = "TBILL",
        period: str = "max",
        interval: str = "1d",
    ) -> pd.DataFrame:

        if symbol != "TBILL":

            raise ValueError(
                "TreasuryBillProvider only supports TBILL"
            )

        self.logger.info(
            "Downloading 3-month Treasury bill history from FRED..."
        )

        with urlopen(
            self.FRED_URL,
            timeout=30,
        ) as response:

            content = response.read().decode("utf-8")

        raw = pd.read_csv(
            StringIO(content),
            parse_dates=["DATE"],
        )

        raw = raw.rename(
            columns={
                "DATE": "Date",
                "DTB3": "Rate",
            }
        )

        raw = raw.set_index("Date")

        #
        # FRED represents missing observations as ".".
        #

        raw["Rate"] = pd.to_numeric(
            raw["Rate"],
            errors="coerce",
        )

        raw = raw.dropna(
            subset=["Rate"]
        )

        if raw.empty:

            raise RuntimeError(
                "FRED returned no valid DTB3 observations"
            )

        #
        # DTB3 is a discount-basis annualized rate.
        #
        # Convert the discount rate to an approximate annual
        # investment yield using a 91-day bill and a 360-day
        # discount convention.
        #
        # d = discount rate
        # y = investment yield
        #
        # y = d * 365 / (360 - d * 91)
        #
        # Rate is supplied by FRED in percent.
        #

        discount = raw["Rate"] / 100.0

        annual_yield = (
            discount * 365.0
            / (
                360.0
                - discount * 91.0
            )
        )

        #
        # Build a synthetic price index.
        #
        # The Treasury rate is an annualized rate, so compound
        # it across the actual number of calendar days between
        # observations. This means weekends and holidays earn
        # interest as they should.
        #

        prices = [100.0]

        dates = raw.index

        for i in range(1, len(dates)):

            previous_date = dates[i - 1]
            current_date = dates[i]

            days = (
                current_date
                - previous_date
            ).days

            rate = annual_yield.iloc[i - 1]

            growth = (
                1.0 + rate
            ) ** (
                days / 365.0
            )

            prices.append(
                prices[-1] * growth
            )

        raw["Close"] = prices

        #
        # Cash has no meaningful OHLC variation.
        #

        raw["Open"] = raw["Close"]
        raw["High"] = raw["Close"]
        raw["Low"] = raw["Close"]

        #
        # No trading volume exists for the synthetic series.
        #

        raw["Volume"] = 0

        df = raw[
            [
                "Open",
                "High",
                "Low",
                "Close",
                "Volume",
            ]
        ]

        df.index.name = None

        if not df.index.is_monotonic_increasing:

            raise RuntimeError(
                "TBILL history returned unsorted data"
            )

        self.logger.info(
            "TBILL downloaded successfully (%d rows)",
            len(df),
        )

        return df