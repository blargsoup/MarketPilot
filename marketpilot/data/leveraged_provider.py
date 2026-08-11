"""
Synthetic leveraged ETF provider.

Creates a continuous history for leveraged ETFs by:

    1. Using the real ETF history from its inception onward.
    2. Reconstructing a synthetic history before inception using:
         - The underlying ETF's daily total return
         - The requested leverage
         - Historical Treasury bill rates as a financing-cost proxy
         - The ETF expense ratio

The synthetic history is intended for historical backtesting, not
for reproducing the exact historical NAV of an ETF that did not yet
exist.
"""

from __future__ import annotations

import pandas as pd


class LeveragedETFProvider:

    def __init__(
        self,
        underlying_provider,
        treasury_provider,
        leverage: float,
        expense_ratio: float,
    ):

        self.underlying_provider = underlying_provider
        self.treasury_provider = treasury_provider
        self.leverage = leverage
        self.expense_ratio = expense_ratio

    def get_history(
        self,
        symbol: str,
        underlying_symbol: str,
        actual_history,
        period: str = "max",
        interval: str = "1d",
    ):

        #
        # Get underlying history.
        #

        underlying = self.underlying_provider.get_history(
            underlying_symbol,
            period=period,
            interval=interval,
        )

        #
        # Get historical Treasury bill rates.
        #

        treasury = self.treasury_provider.get_history(
            "TBILL",
            period=period,
            interval=interval,
        )

        underlying_df = underlying.copy()
        actual_df = actual_history.copy()
        treasury_df = treasury.copy()

        #
        # Normalize indexes.
        #

        underlying_df.index = pd.to_datetime(
            underlying_df.index
        )

        actual_df.index = pd.to_datetime(
            actual_df.index
        )

        treasury_df.index = pd.to_datetime(
            treasury_df.index
        )

        #
        # We use adjusted close because it represents the
        # underlying ETF's total-return history.
        #

        if "Adj Close" in underlying_df.columns:

            underlying_close = underlying_df[
                "Adj Close"
            ]

        else:

            underlying_close = underlying_df[
                "Close"
            ]

        #
        # Determine the actual ETF inception date.
        #

        actual_start = actual_df.index.min()

        #
        # Only create synthetic history before the real ETF existed.
        #

        synthetic_underlying = underlying_close[
            underlying_close.index < actual_start
        ].copy()

        if synthetic_underlying.empty:

            return actual_df

        #
        # Treasury rates.
        #
        # TBILL is represented as an annualized percentage,
        # e.g. 5.00 means 5%.
        #

        if "Close" in treasury_df.columns:

            treasury_rate = treasury_df["Close"].copy()

        elif "Adj Close" in treasury_df.columns:

            treasury_rate = treasury_df["Adj Close"].copy()

        else:

            raise ValueError(
                "TBILL history must contain a Close or "
                "Adj Close column."
            )

        #
        # FRED's DTB3 series is expressed as a percentage.
        #
        # Convert:
        #
        #     5.00 -> 0.05
        #

        treasury_rate = treasury_rate / 100.0

        #
        # Align Treasury data to the QQQ trading dates.
        #
        # Forward-fill weekends / holidays and missing observations.
        #

        financing_rate = (
            treasury_rate
            .reindex(
                synthetic_underlying.index
            )
            .ffill()
            .bfill()
        )

        #
        # Daily QQQ total return.
        #

        underlying_return = (
            synthetic_underlying
            .pct_change()
        )

        #
        # First observation cannot have a return.
        #

        underlying_return = underlying_return.dropna()

        financing_rate = financing_rate.reindex(
            underlying_return.index
        ).ffill().bfill()

        #
        # Convert annual expense ratio into a daily drag.
        #

        daily_expense = (
            self.expense_ratio / 252.0
        )

        #
        # Approximate financing cost.
        #
        # A leveraged position has approximately
        # (leverage - 1) times the underlying exposure
        # financed.
        #
        # Example:
        #
        # 2x QQQ -> approximately 1x financed
        # 3x QQQ -> approximately 2x financed
        #

        daily_financing = (
            (self.leverage - 1.0)
            * financing_rate
            / 252.0
        )

        #
        # Synthetic daily leveraged return.
        #

        leveraged_return = (
            self.leverage
            * underlying_return
            - daily_financing
            - daily_expense
        )

        #
        # We need to anchor the synthetic series to the actual
        # ETF at inception.
        #
        # Start with the first actual ETF close and work backward.
        #

        first_actual_close = float(
            actual_df["Close"].iloc[0]
        )

        synthetic_values = pd.Series(
            index=leveraged_return.index,
            dtype=float,
        )

        #
        # Reverse the daily return relationship:
        #
        #     tomorrow = today * (1 + return)
        #
        # therefore:
        #
        #     today = tomorrow / (1 + return)
        #

        next_value = first_actual_close

        for date in reversed(
            leveraged_return.index
        ):

            daily_return = float(
                leveraged_return.loc[date]
            )

            previous_value = (
                next_value
                / (1.0 + daily_return)
            )

            synthetic_values.loc[date] = (
                previous_value
            )

            next_value = previous_value

        #
        # Build synthetic OHLC data.
        #
        # The exact historical OHLC of a non-existent leveraged
        # ETF cannot be known, so we construct a synthetic Close
        # series and use it consistently.
        #

        synthetic_df = pd.DataFrame(
            index=synthetic_values.index
        )

        synthetic_df["Open"] = synthetic_values
        synthetic_df["High"] = synthetic_values
        synthetic_df["Low"] = synthetic_values
        synthetic_df["Close"] = synthetic_values

        synthetic_df["Adj Close"] = synthetic_values

        #
        # Volume does not meaningfully exist for a synthetic ETF.
        #

        synthetic_df["Volume"] = 0

        #
        # Combine synthetic history with the real ETF history.
        #

        combined = pd.concat(
            [
                synthetic_df,
                actual_df,
            ]
        )

        #
        # Remove duplicate dates.
        #
        # Real ETF data wins at inception.
        #

        combined = (
            combined[
                ~combined.index.duplicated(
                    keep="last"
                )
            ]
            .sort_index()
        )

        return combined