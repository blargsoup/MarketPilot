"""
Synthetic leveraged ETF provider.

Creates a continuous historical series for leveraged ETFs by:

1. Using the real ETF history from its inception onward.
2. Reconstructing a synthetic pre-inception history using:
   - The underlying ETF's daily total return
   - Daily leverage
   - Historical Treasury bill rates as a financing proxy
   - ETF expense ratio

The synthetic history is intended for historical research and
backtesting. It is not intended to reproduce the exact historical
NAV of an ETF that did not yet exist.
"""

from __future__ import annotations

import math

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

        def validate_history(
            self,
            symbol: str,
            history: pd.DataFrame,
        ) -> None:

            if history.empty:
                raise ValueError(
                    f"{symbol} history is empty."
                )

            if "Close" not in history.columns:
                raise ValueError(
                    f"{symbol} history has no Close column."
                )

            close = history["Close"]

            if close.isna().any():
                raise ValueError(
                    f"{symbol} history contains NaN closes."
                )

            if not close.apply(math.isfinite).all():
                raise ValueError(
                    f"{symbol} history contains non-finite closes."
                )

            if (close <= 0).any():
                bad = close[close <= 0]

                raise ValueError(
                    f"{symbol} history contains "
                    f"{len(bad)} zero/negative prices."
                )

    #####

    def validate_history(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> None:
        """
        Validate a completed leveraged ETF history.

        Synthetic histories must never contain missing, non-finite,
        or non-positive prices because those can silently corrupt
        backtest results.
        """

        if df is None or df.empty:
            raise ValueError(
                f"{symbol}: history is empty"
            )

        required_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Adj Close",
        ]

        missing = [
            column
            for column in required_columns
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                f"{symbol}: missing columns: {missing}"
            )

        if not isinstance(
            df.index,
            pd.DatetimeIndex,
        ):
            raise ValueError(
                f"{symbol}: index must be a DatetimeIndex"
            )

        if df.index.has_duplicates:
            raise ValueError(
                f"{symbol}: duplicate dates detected"
            )

        if not df.index.is_monotonic_increasing:
            raise ValueError(
                f"{symbol}: dates are not sorted"
            )

        prices = df[required_columns]

        if prices.isna().any().any():
            raise ValueError(
                f"{symbol}: NaN prices detected"
            )

        if not prices.apply(
            lambda column: pd.Series(
                pd.notna(column)
                & (column != float("inf"))
                & (column != float("-inf")),
                index=column.index,
            ).all()
        ).all():
            raise ValueError(
                f"{symbol}: infinite prices detected"
            )

        for column in required_columns:
            if (df[column] <= 0).any():
                bad_date = df.index[
                    df[column] <= 0
                ][0]

                bad_value = df.loc[
                    bad_date,
                    column,
                ]

                raise ValueError(
                    f"{symbol}: non-positive {column} "
                    f"value {bad_value} on {bad_date}"
                )

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
        # Get historical financing rates.
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

        underlying_df = underlying_df.sort_index()
        actual_df = actual_df.sort_index()
        treasury_df = treasury_df.sort_index()

        #
        # Determine actual ETF inception date.
        #

        actual_start = actual_df.index.min()

        #
        # We only synthesize history before the real ETF existed.
        #

        synthetic_underlying = underlying_df[
            underlying_df.index < actual_start
        ].copy()

        if synthetic_underlying.empty:
            return actual_df

        #
        # Select underlying total-return price.
        #
        # Adj Close is preferred because it incorporates
        # distributions.
        #

        if "Adj Close" in synthetic_underlying.columns:
            underlying_close = synthetic_underlying[
                "Adj Close"
            ].copy()

        else:
            underlying_close = synthetic_underlying[
                "Close"
            ].copy()

        #
        # Remove invalid underlying prices.
        #

        underlying_close = underlying_close[
            underlying_close.notna()
        ]

        underlying_close = underlying_close[
            underlying_close > 0
        ]

        if len(underlying_close) < 2:
            raise ValueError(
                f"Insufficient underlying history to synthesize "
                f"{symbol}."
            )

        #
        # Treasury rate.
        #

        if "Close" in treasury_df.columns:
            treasury_rate = treasury_df[
                "Close"
            ].copy()

        elif "Adj Close" in treasury_df.columns:
            treasury_rate = treasury_df[
                "Adj Close"
            ].copy()

        else:
            raise ValueError(
                "TBILL history must contain a Close or "
                "Adj Close column."
            )

        #
        # FRED DTB3 is expressed as a percentage.
        #
        # Example:
        #
        # 5.00 -> 0.05
        #

        treasury_rate = treasury_rate / 100.0

        #
        # Align financing rate with underlying trading dates.
        #

        financing_rate = (
            treasury_rate
            .reindex(underlying_close.index)
            .ffill()
            .bfill()
        )

        #
        # Daily underlying return.
        #

        underlying_return = (
            underlying_close.pct_change()
        )

        underlying_return = (
            underlying_return.dropna()
        )

        financing_rate = (
            financing_rate
            .reindex(underlying_return.index)
            .ffill()
            .bfill()
        )

        #
        # Annual expense ratio -> daily expense drag.
        #

        daily_expense = (
            self.expense_ratio / 252.0
        )

        #
        # Approximate financing cost.
        #
        # For:
        #
        # 2x -> finance approximately 1x
        # 3x -> finance approximately 2x
        #

        daily_financing = (
            (self.leverage - 1.0)
            * financing_rate
            / 252.0
        )

        #
        # Synthetic leveraged daily return.
        #

        leveraged_return = (
            self.leverage
            * underlying_return
            - daily_financing
            - daily_expense
        )

        #
        # A leveraged ETF cannot have a daily loss below -100%.
        #
        # This also protects the reconstruction from producing
        # zero/negative prices when an extreme underlying move
        # occurs.
        #

        leveraged_return = leveraged_return.clip(
            lower=-0.999999
        )

        #
        # ----------------------------------------------------------
        # Build the synthetic history FORWARD.
        # ----------------------------------------------------------
        #
        # We first create a normalized synthetic series beginning
        # at 1.0.
        #
        # This is much safer than recursively working backwards
        # from the real ETF price.
        #

        synthetic_normalized = (
            (1.0 + leveraged_return)
            .cumprod()
        )

        #
        # The last synthetic value before inception becomes the
        # anchor point for the real ETF.
        #

        if synthetic_normalized.empty:
            return actual_df

        synthetic_last = float(
            synthetic_normalized.iloc[-1]
        )

        actual_first_close = float(
            actual_df["Close"].iloc[0]
        )

        if (
            not math.isfinite(actual_first_close)
            or actual_first_close <= 0
        ):
            raise ValueError(
                f"Invalid first actual {symbol} close: "
                f"{actual_first_close}"
            )

        #
        # Scale the entire synthetic series so that its final
        # pre-inception value matches the first actual ETF close.
        #

        scale_factor = (
            actual_first_close
            / synthetic_last
        )

        synthetic_values = (
            synthetic_normalized
            * scale_factor
        )

        #
        # ----------------------------------------------------------
        # Build synthetic OHLC data.
        # ----------------------------------------------------------
        #

        synthetic_df = pd.DataFrame(
            index=synthetic_values.index
        )

        synthetic_df["Open"] = synthetic_values
        synthetic_df["High"] = synthetic_values
        synthetic_df["Low"] = synthetic_values
        synthetic_df["Close"] = synthetic_values
        synthetic_df["Adj Close"] = synthetic_values
        synthetic_df["Volume"] = 0

        #
        # ----------------------------------------------------------
        # Validate synthetic history.
        # ----------------------------------------------------------
        #

        if not synthetic_df["Close"].notna().all():
            raise ValueError(
                f"Synthetic {symbol} history contains NaN values."
            )

        if not synthetic_df["Close"].apply(
            math.isfinite
        ).all():
            raise ValueError(
                f"Synthetic {symbol} history contains "
                f"non-finite values."
            )

        if (synthetic_df["Close"] <= 0).any():
            raise ValueError(
                f"Synthetic {symbol} history contains "
                f"zero/negative prices."
            )

        #
        # ----------------------------------------------------------
        # Validate handoff to actual ETF.
        # ----------------------------------------------------------
        #

        last_synthetic_close = float(
            synthetic_df["Close"].iloc[-1]
        )

        #
        # The synthetic series should end very close to the
        # first actual close.
        #
        # They may differ slightly because the actual ETF's first
        # trading day is not itself included in the synthetic
        # series.
        #

        handoff_ratio = (
            actual_first_close
            / last_synthetic_close
        )

        if not (
            0.95
            <= handoff_ratio
            <= 1.05
        ):
            raise ValueError(
                f"{symbol} synthetic/actual handoff is "
                f"outside tolerance: "
                f"{handoff_ratio:.4f}"
            )

        #
        # Combine synthetic history with actual history.
        #

        combined = pd.concat(
            [
                synthetic_df,
                actual_df,
            ]
        )

        #
        # Real ETF data wins if a date overlaps.
        #

        combined = (
            combined[
                ~combined.index.duplicated(
                    keep="last"
                )
            ]
            .sort_index()
        )

        self.validate_history(
            symbol,
            combined,
        )

        #
        # Handoff diagnostics.
        #

        if not synthetic_df.empty:

            synthetic_last_date = (
                synthetic_df.index[-1]
            )

            synthetic_last_close = float(
                synthetic_df["Close"].iloc[-1]
            )

            actual_first_date = actual_df.index[0]

            actual_first_close = float(
                actual_df["Close"].iloc[0]
            )

            print(
                f"Synthetic {symbol}:"
            )

            print(
                f"    Synthetic last : "
                f"{synthetic_last_date.date()} "
                f"${synthetic_last_close:.6f}"
            )

            print(
                f"    Actual first   : "
                f"{actual_first_date.date()} "
                f"${actual_first_close:.6f}"
            )

            print(
                f"    Handoff ratio  : "
                f"{actual_first_close / synthetic_last_close:.4f}"
            )

            print(
                f"    Synthetic first: "
                f"{synthetic_df.index[0].date()} "
                f"${synthetic_df['Close'].iloc[0]:.6f}"
            )

        return combined