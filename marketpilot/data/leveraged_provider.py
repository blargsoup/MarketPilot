"""
Synthetic leveraged ETF provider.

Creates a continuous historical series for leveraged ETFs by:

1. Using the real ETF history from its inception onward.
2. Reconstructing a synthetic pre-inception history using:
   - The underlying ETF's daily total return
   - Daily leverage
   - Historical Treasury bill rates as a financing proxy
   - ETF expense ratio
3. Maintaining a separate synthetic NAV/wealth layer.
4. Maintaining a split-aware synthetic share-price layer.

Important:

The synthetic NAV represents economic portfolio wealth.

The synthetic share price is a denomination of that NAV and may
undergo splits/re-denominations without changing portfolio wealth.

This distinction is important for leveraged ETFs because historical
3x daily compounding can drive the economic NAV extremely close to
zero during severe drawdowns, while a real ETF can subsequently use
reverse splits to keep its quoted share price usable.

The synthetic history is intended for historical research and
backtesting. It is not intended to reproduce the exact historical
NAV of an ETF that did not yet exist.
"""

from __future__ import annotations

import logging
import math

import pandas as pd

logger = logging.getLogger(__name__)


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

    # ------------------------------------------------------------------
    # Historical synthetic split information
    # ------------------------------------------------------------------

    @staticmethod
    def _historical_split_factors(symbol: str) -> dict:
        """
        Return known historical split factors for the synthetic
        pre-inception share-price layer.

        Split convention:

            2.0  = 2-for-1 forward split
            0.25 = 1-for-4 reverse split

        These factors affect the quoted share price only.

        They do NOT affect NAV/portfolio wealth.
        """

        symbol = symbol.upper()

        # Historical synthetic TQQQ split information supplied for
        # the MarketPilot reconstruction.
        if symbol == "TQQQ":
            return {
                pd.Timestamp("2000-01-21"): 0.25,
                pd.Timestamp("2000-06-13"): 2.0,
                pd.Timestamp("2000-07-19"): 2.0,
                pd.Timestamp("2000-08-30"): 2.0,
                pd.Timestamp("2005-11-29"): 0.25,
                pd.Timestamp("2006-11-03"): 2.0,
                pd.Timestamp("2007-01-08"): 2.0,
                pd.Timestamp("2007-05-17"): 2.0,
                pd.Timestamp("2007-11-09"): 2.0,
                pd.Timestamp("2008-03-03"): 2.0,
                pd.Timestamp("2008-03-28"): 2.0,
                pd.Timestamp("2008-06-10"): 2.0,
                pd.Timestamp("2008-07-29"): 2.0,
                pd.Timestamp("2009-01-09"): 2.0,
                pd.Timestamp("2009-06-23"): 0.25,
            }

        return {}

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Split column normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_split_series(
        df: pd.DataFrame,
    ) -> pd.Series:
        """
        Find a split column regardless of whether the source uses
        Yahoo/yfinance naming or the CSV-style 'split' naming.
        """

        candidates = [
            "Stock Splits",
            "Split",
            "split",
            "stock_splits",
        ]

        for column in candidates:
            if column in df.columns:
                splits = pd.to_numeric(
                    df[column],
                    errors="coerce",
                ).fillna(1.0)

                splits = splits.replace(
                    [float("inf"), float("-inf")],
                    1.0,
                )

                splits = splits.where(
                    splits > 0,
                    1.0,
                )

                return splits

        return pd.Series(
            1.0,
            index=df.index,
            dtype=float,
        )

    # ------------------------------------------------------------------
    # Synthetic price denomination
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_synthetic_price_denominations(
        nav: pd.Series,
        historical_splits: pd.Series,
        target_price: float,
        minimum_price: float = 10.0,
        maximum_price: float = 200.0,
    ):
        """
        Convert NAV into a usable synthetic share price.

        NAV represents wealth and is NEVER modified.

        The share price is simply:

            share_price = NAV / share_count

        Historical splits modify share_count.

        In addition, if the synthetic price becomes wildly impractical,
        an internal denomination split is applied. This is equivalent
        to changing the number of shares while preserving total wealth.

        This prevents pathological historical prices such as:

            $1e-148
            $1e+150

        from entering the dataframe.

        The generated denomination splits are recorded separately from
        the supplied historical splits.
        """

        if nav.empty:
            return (
                pd.Series(dtype=float),
                pd.Series(dtype=float),
            )

        nav = nav.astype(float)

        historical_splits = (
            historical_splits
            .reindex(nav.index)
            .fillna(1.0)
        )

        prices = []
        applied_splits = []

        # Start with one synthetic share.
        shares = 1.0

        # We will choose the initial share count after looking at
        # the first NAV and desired starting price.
        first_nav = float(nav.iloc[0])

        if not math.isfinite(first_nav) or first_nav <= 0:
            first_nav = 1.0

        shares = first_nav / target_price

        if not math.isfinite(shares) or shares <= 0:
            shares = 1.0

        for date in nav.index:
            nav_value = float(nav.loc[date])

            if not math.isfinite(nav_value):
                nav_value = 0.0

            # ----------------------------------------------------------
            # Apply the historical split.
            #
            # A factor of:
            #
            #   2.0  -> 2-for-1 split
            #   0.25 -> 1-for-4 reverse split
            #
            # Share count changes by the split factor.
            #
            # NAV does not change.
            # ----------------------------------------------------------

            historical_split = float(
                historical_splits.loc[date]
            )

            if (
                math.isfinite(historical_split)
                and historical_split > 0
                and not math.isclose(
                    historical_split,
                    1.0,
                )
            ):
                shares *= historical_split

            # ----------------------------------------------------------
            # Calculate current quoted price.
            # ----------------------------------------------------------

            if shares > 0:
                price = nav_value / shares
            else:
                price = target_price

            # ----------------------------------------------------------
            # Synthetic denomination split.
            #
            # These do NOT alter NAV.
            #
            # If price is too low:
            #
            #   reverse split -> fewer shares -> higher price
            #
            # If price is too high:
            #
            #   forward split -> more shares -> lower price
            #
            # We use 4-for-1 / 1-for-4 denominations because these are
            # common ETF-style split sizes.
            # ----------------------------------------------------------

            denomination_split = 1.0

            if (
                price > 0
                and math.isfinite(price)
            ):
                while price < minimum_price:
                    shares *= 0.25
                    denomination_split *= 0.25

                    price = (
                        nav_value / shares
                        if shares > 0
                        else target_price
                    )

                while price > maximum_price:
                    shares *= 2.0
                    denomination_split *= 2.0

                    price = (
                        nav_value / shares
                        if shares > 0
                        else target_price
                    )

            # ----------------------------------------------------------
            # If NAV is numerically zero, preserve a sane quoted price
            # rather than allowing 0.0 into the price dataframe.
            #
            # This does NOT change the NAV itself.
            # ----------------------------------------------------------

            if (
                not math.isfinite(price)
                or price <= 0
            ):
                price = target_price

            prices.append(price)
            applied_splits.append(
                historical_split
                * denomination_split
            )

        synthetic_price = pd.Series(
            prices,
            index=nav.index,
            dtype=float,
        )

        applied_split_series = pd.Series(
            applied_splits,
            index=nav.index,
            dtype=float,
        )

        return (
            synthetic_price,
            applied_split_series,
        )

    # ------------------------------------------------------------------
    # Main history builder
    # ------------------------------------------------------------------

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

        #
        # Yahoo may return an all-NaN Adj Close column for
        # leveraged ETFs. For this synthetic reconstruction,
        # Close is our authoritative price series.
        #

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
        # ----------------------------------------------------------
        # EXISTING SYNTHETIC DAILY RETURN CALCULATION
        # ----------------------------------------------------------
        #
        # Keep this calculation unchanged.
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

        leveraged_return = leveraged_return.clip(
            lower=-0.999999
        )

        #
        # ----------------------------------------------------------
        # BUILD ECONOMIC NAV
        # ----------------------------------------------------------
        #
        # NAV is the wealth layer.
        #
        # Start at 1.0.
        #
        # IMPORTANT:
        #
        # Splits are NOT applied here.
        #
        # A split must never change portfolio wealth.
        #

        nav = (
            1.0
            * (1.0 + leveraged_return)
            .cumprod()
        )

        if nav.empty:
            return actual_df

        #
        # ----------------------------------------------------------
        # BUILD SPLIT-AWARE SYNTHETIC SHARE PRICE
        # ----------------------------------------------------------
        #

        historical_split_map = (
            self._historical_split_factors(symbol)
        )

        historical_splits = pd.Series(
            1.0,
            index=nav.index,
            dtype=float,
        )

        for date, split_factor in (
            historical_split_map.items()
        ):
            if date in historical_splits.index:
                historical_splits.loc[date] = (
                    float(split_factor)
                )

        #
        # Use the first actual ETF close as the reference price.
        #
        # This is ONLY a price denomination.
        #
        # It does not alter NAV.
        #

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
        # Start synthetic shares so that the first synthetic
        # price is in a normal ETF range.
        #

        synthetic_target_price = 50.0

        #
        # We construct the share price using the NAV.
        #
        # To make the final synthetic price line up with the real
        # ETF, first calculate the scale required at the handoff.
        #

        synthetic_last_nav = float(
            nav.iloc[-1]
        )

        if (
            not math.isfinite(synthetic_last_nav)
            or synthetic_last_nav <= 0
        ):
            synthetic_last_nav = 1e-300

        #
        # Base share count required for the handoff.
        #
        # We deliberately keep this separate from NAV.
        #

        base_shares = (
            synthetic_last_nav
            / actual_first_close
        )

        if (
            not math.isfinite(base_shares)
            or base_shares <= 0
        ):
            base_shares = (
                synthetic_last_nav
                / synthetic_target_price
            )

        #
        # Calculate the split-aware share price.
        #

        synthetic_price, applied_splits = (
            self._apply_synthetic_price_denominations(
                nav=nav,
                historical_splits=historical_splits,
                target_price=synthetic_target_price,
            )
        )

        #
        # ----------------------------------------------------------
        # Re-anchor price layer to the actual ETF.
        # ----------------------------------------------------------
        #
        # This is a PRICE scaling operation only.
        #
        # NAV remains untouched.
        #

        synthetic_last_price = float(
            synthetic_price.iloc[-1]
        )

        if (
            not math.isfinite(synthetic_last_price)
            or synthetic_last_price <= 0
        ):
            raise ValueError(
                f"Synthetic {symbol} price layer produced "
                f"an invalid final price: "
                f"{synthetic_last_price}"
            )

        price_scale = (
            actual_first_close
            / synthetic_last_price
        )

        synthetic_price = (
            synthetic_price
            * price_scale
        )

        #
        # Prevent tiny floating-point values from becoming zero.
        #

        synthetic_price = synthetic_price.clip(
            lower=1e-8
        )

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
        synthetic_df["Adj Close"] = synthetic_price

        #
        # Keep the economic NAV available for diagnostics.
        #

        synthetic_df["NAV"] = nav

        #
        # Keep split information available for diagnostics/reporting.
        #

        synthetic_df["Split"] = applied_splits

        synthetic_df["Volume"] = 0

        #
        # ----------------------------------------------------------
        # Validate synthetic history.
        # ----------------------------------------------------------
        #

        if not synthetic_df["Close"].notna().all():
            raise ValueError(
                f"Synthetic {symbol} history contains "
                f"NaN values."
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
        # Combine synthetic history with actual history.
        # ----------------------------------------------------------
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

        #
        # ----------------------------------------------------------
        # Handoff window diagnostics.
        # ----------------------------------------------------------
        #

        handoff_start = actual_df.index.min()

        logger.info(
            f"{symbol} handoff window:"
        )

        handoff_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Adj Close",
        ]

        logger.info(
            "\n"
            +
            combined.loc[
                handoff_start - pd.Timedelta(days=5):
                handoff_start + pd.Timedelta(days=5),
                handoff_columns,
            ].to_string()
        )

        #
        # Validate the completed price history.
        #

        self.validate_history(
            combined[
                [
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Adj Close",
                ]
            ],
            symbol,
        )

        #
        # ----------------------------------------------------------
        # Synthetic diagnostics.
        # ----------------------------------------------------------
        #

        if not synthetic_df.empty:

            synthetic_last_date = (
                synthetic_df.index[-1]
            )

            synthetic_last_close = float(
                synthetic_df["Close"].iloc[-1]
            )

            synthetic_first_date = (
                synthetic_df.index[0]
            )

            synthetic_first_close = float(
                synthetic_df["Close"].iloc[0]
            )

            synthetic_last_nav = float(
                synthetic_df["NAV"].iloc[-1]
            )

            synthetic_min_price = float(
                synthetic_df["Close"].min()
            )

            synthetic_max_price = float(
                synthetic_df["Close"].max()
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
                f"{actual_df.index[0].date()} "
                f"${actual_first_close:.6f}"
            )

            print(
                f"    Price ratio    : "
                f"{actual_first_close / synthetic_last_close:.4f}"
            )

            print(
                f"    Synthetic first: "
                f"{synthetic_first_date.date()} "
                f"${synthetic_first_close:.6f}"
            )

            print(
                f"    Synthetic min  : "
                f"${synthetic_min_price:.6f}"
            )

            print(
                f"    Synthetic max  : "
                f"${synthetic_max_price:.6f}"
            )

            print(
                f"    Synthetic NAV  : "
                f"{synthetic_last_nav:.12g}"
            )

            split_dates = (
                synthetic_df[
                    synthetic_df["Split"] != 1.0
                ].index
            )

            if len(split_dates) > 0:
                print(
                    f"    Synthetic splits: "
                    f"{len(split_dates)}"
                )

        return combined