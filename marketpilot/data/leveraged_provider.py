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
import logging
import pandas as pd
logger = logging.getLogger(__name__)

#
# Historical synthetic TQQQ split factors.
#
# split = 2.0  -> 2-for-1 forward split
# split = 0.25 -> 1-for-4 reverse split
#
# These affect share price only.
# They have ZERO effect on portfolio wealth/NAV.
#
HISTORICAL_SPLITS = {
    "2000-01-21": 0.25,
    "2000-06-13": 2.0,
    "2000-07-19": 2.0,
    "2000-08-30": 2.0,
    "2005-11-29": 0.25,
    "2006-11-03": 2.0,
    "2007-01-08": 2.0,
    "2007-05-17": 2.0,
    "2007-11-09": 2.0,
    "2008-03-03": 2.0,
    "2008-03-28": 2.0,
    "2008-06-10": 2.0,
    "2008-07-29": 2.0,
    "2009-01-09": 2.0,
    "2009-06-23": 0.25,
    "2011-02-25": 2.0,
}


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

            nan_summary = (
                prices.isna()
                .sum()
                .loc[lambda x: x > 0]
                .to_dict()
            )

            nan_rows = prices[
                prices.isna().any(axis=1)
            ]

            first_nan_date = nan_rows.index.min()
            last_nan_date = nan_rows.index.max()

            raise ValueError(
                f"{symbol}: NaN prices detected. "
                f"Columns: {nan_summary}. "
                f"First date: {first_nan_date}. "
                f"Last date: {last_nan_date}. "
                f"Rows affected: {len(nan_rows)}"
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

        ####################################
        # Yahoo may return an all-NaN Adj Close column for
        # leveraged ETFs. For this synthetic reconstruction,
        # Close is our authoritative price series.
        #
        # If Adj Close is missing or entirely NaN, use Close.
        if (
            "Adj Close" not in actual_df.columns
            or actual_df["Adj Close"].isna().all()
        ):
            actual_df["Adj Close"] = actual_df["Close"]

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
        # Modern U.S. equity markets have a 20% Level 1 circuit breaker.
        # For the historical synthetic reconstruction, cap the underlying
        # daily loss at -20% BEFORE applying leverage.
        #
        # This is important because TQQQ/QLD reset their leverage daily.
        #
        # Example:
        #
        #   QQQ daily return = -20%
        #   QLD synthetic return ~= -40%
        #   TQQQ synthetic return ~= -60%
        #
        # We intentionally do NOT cap the leveraged ETF at -20%.
        #

        MAX_UNDERLYING_DAILY_LOSS = -0.20

        capped_underlying_return = underlying_return.clip(
            lower=MAX_UNDERLYING_DAILY_LOSS
        )

        leveraged_return = (
            self.leverage
            * capped_underlying_return
            - daily_financing
            - daily_expense
        )

        #
        # A leveraged ETF cannot have a daily loss below -100%.
        #
        # This is a final mathematical safety check. Under the
        # -20% underlying circuit-breaker assumption, normal 2x/3x
        # leverage should never come close to this limit.
        #

        leveraged_return = leveraged_return.clip(
            lower=-0.999999
        )

        #
        # ----------------------------------------------------------
        # Build split-aware synthetic NAV and share price.
        # ----------------------------------------------------------
        #
        # IMPORTANT:
        #
        # The leveraged daily return calculation above is the
        # authoritative portfolio wealth calculation.
        #
        # Splits must NEVER modify that wealth calculation.
        #
        # We therefore maintain two separate concepts:
        #
        #   1. synthetic_nav
        #      True compounded portfolio wealth.
        #
        #   2. synthetic_price
        #      A share-price representation of that wealth.
        #
        # A split changes the number of shares and the share price,
        # but leaves NAV/wealth unchanged.
        #
        # This separation prevents historical splits from corrupting
        # the actual backtest return.
        #

        synthetic_nav = (
            (1.0 + leveraged_return)
            .cumprod()
        )

        if synthetic_nav.empty:
            return actual_df

        #
        # ----------------------------------------------------------
        # Build split-aware share price.
        # ----------------------------------------------------------
        #
        # We use a normalized share-price series rather than scaling
        # the synthetic NAV to the first real ETF price.
        #
        # This is intentional.
        #
        # The pre-inception synthetic NAV can become extremely small
        # during periods such as the dot-com collapse. Scaling that
        # tiny NAV to the first real TQQQ price creates astronomical
        # historical prices.
        #
        # The share-price layer is therefore independent of that
        # arbitrary handoff scale.
        #

        SYNTHETIC_START_PRICE = 100.0

        synthetic_price = pd.Series(
            index=synthetic_nav.index,
            dtype=float,
        )

        current_price = SYNTHETIC_START_PRICE

        for date in synthetic_nav.index:

            daily_return = float(
                leveraged_return.loc[date]
            )

            #
            # First apply the actual investment return.
            #
            current_price *= (1.0 + daily_return)

            #
            # Then apply any historical split occurring on
            # this date.
            #
            split_factor = HISTORICAL_SPLITS.get(
                date.strftime("%Y-%m-%d"),
                1.0,
            )

            if split_factor <= 0:
                raise ValueError(
                    f"Invalid split factor "
                    f"{split_factor} on {date}."
                )

            #
            # A 2-for-1 split:
            #
            #   price -> price / 2
            #   shares -> shares * 2
            #
            # A 1-for-4 reverse split:
            #
            #   price -> price / 0.25
            #   shares -> shares * 0.25
            #
            # In both cases portfolio wealth is unchanged.
            #
            if split_factor != 1.0:
                current_price /= split_factor

                logger.debug(
                    "Synthetic %s split on %s: "
                    "factor=%.4f price=%.6f",
                    symbol,
                    date.date(),
                    split_factor,
                    current_price,
                )

            synthetic_price.loc[date] = current_price

        #
        # ----------------------------------------------------------
        # Build synthetic OHLC data.
        # ----------------------------------------------------------
        #

        synthetic_df = pd.DataFrame(
            index=synthetic_price.index
        )

        synthetic_df["Open"] = synthetic_price
        synthetic_df["High"] = synthetic_price
        synthetic_df["Low"] = synthetic_price
        synthetic_df["Close"] = synthetic_price

        #
        # For the synthetic pre-inception history, the synthetic
        # Close is our authoritative price representation.
        #
        synthetic_df["Adj Close"] = synthetic_price

        synthetic_df["Volume"] = 0

        #
        # Keep the actual compounded wealth available for diagnostics.
        #
        synthetic_df["Synthetic NAV"] = synthetic_nav

        #
        # Keep the split factor visible in the resulting data.
        #
        synthetic_df["Split"] = [
            HISTORICAL_SPLITS.get(
                date.strftime("%Y-%m-%d"),
                1.0,
            )
            for date in synthetic_price.index
        ]

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


        logger.info(
            f"{symbol} history validation: "
            f"{len(combined)} rows, "
            f"{combined.index.min().date()} -> "
            f"{combined.index.max().date()}"
        )

        logger.info(
            f"{symbol} actual history: "
            f"{len(actual_df)} rows, "
            f"{actual_df.index.min().date()} -> "
            f"{actual_df.index.max().date()}"
        )

        logger.info(
            f"{symbol} synthetic history: "
            f"{len(synthetic_df)} rows, "
            f"{synthetic_df.index.min().date()} -> "
            f"{synthetic_df.index.max().date()}"
        )

        handoff_start = actual_df.index.min()

        logger.info(
            f"{symbol} handoff window:"
        )

        logger.info(
            "\n" +
            combined.loc[
                handoff_start - pd.Timedelta(days=5):
                handoff_start + pd.Timedelta(days=5),
                [
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Adj Close",
                ],
            ].to_string()
        )

        self.validate_history(
            combined,
            symbol,
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