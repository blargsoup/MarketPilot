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

        #
        # Parse the CSV first without assuming column names.
        #

        raw = pd.read_csv(
            StringIO(content)
        )

        #
        # Normalize column names.
        #

        raw.columns = [
            str(column).strip().upper()
            for column in raw.columns
        ]

        #
        # FRED normally returns DATE and DTB3.
        # Find them explicitly so that we get a useful error
        # if the endpoint returns something unexpected.
        #

        date_column = None
        rate_column = None

        for column in raw.columns:

            if column in (
                "DATE",
                "DATE_TIME",
                "TIME",
                "OBSERVATION_DATE",
            ):

                date_column = column

            if column == "DTB3":

                rate_column = column

        if date_column is None:

            raise ValueError(
                "Could not find date column in FRED response. "
                f"Columns returned: {list(raw.columns)}"
            )

        if rate_column is None:

            raise ValueError(
                "Could not find DTB3 column in FRED response. "
                f"Columns returned: {list(raw.columns)}"
            )

        #
        # Parse dates.
        #

        raw[date_column] = pd.to_datetime(
            raw[date_column],
            errors="coerce",
        )

        #
        # Convert FRED's '.' missing values to NaN.
        #

        raw[rate_column] = pd.to_numeric(
            raw[rate_column],
            errors="coerce",
        )

        #
        # Remove invalid observations.
        #

        raw = raw.dropna(
            subset=[
                date_column,
                rate_column,
            ]
        )

        if raw.empty:

            raise RuntimeError(
                "FRED returned no valid DTB3 observations"
            )

        raw = raw.set_index(
            date_column
        )

        raw = raw.sort_index()

        #
        # FRED DTB3 is the 3-month Treasury bill secondary-market
        # rate quoted on a discount basis.
        #
        # Convert the discount rate into an approximate investment
        # yield using the standard 91-day bill / 360-day convention.
        #

        discount = raw[rate_column] / 100.0

        annual_yield = (
            discount * 365.0
            /
            (
                360.0
                -
                discount * 91.0
            )
        )

        #
        # Preserve the annualized Treasury yield separately.
        #
        # The leveraged synthetic ETF engine needs the actual annual
        # financing rate, not the synthetic cash price index.
        #
        raw["Rate"] = annual_yield

        #
        # Build a synthetic total-return price index.
        #
        # Start at 100.
        #
        # Interest earned between observations is based on the
        # previous observation's annualized yield.
        #
        # This naturally includes weekend and holiday accrual.
        #

        prices = [100.0]

        dates = raw.index

        for i in range(1, len(dates)):

            previous_date = dates[i - 1]
            current_date = dates[i]

            days = (
                current_date
                -
                previous_date
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
        # Synthetic cash has no intraday price movement.
        #

        raw["Open"] = raw["Close"]
        raw["High"] = raw["Close"]
        raw["Low"] = raw["Close"]

        #
        # No meaningful trading volume exists.
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