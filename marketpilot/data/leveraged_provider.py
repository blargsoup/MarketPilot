"""
Synthetic leveraged ETF provider.

Creates a continuous historical series for leveraged ETFs by:

1. Using the real ETF history from its inception onward.
2. Reconstructing a synthetic pre-inception history using:
   - The underlying ETF's daily total return
   - Daily leverage
   - Daily financing cost
   - ETF expense ratio
3. Maintaining a separate synthetic economic NAV/wealth layer.
4. Maintaining a split-aware synthetic share-price layer.

IMPORTANT:

The synthetic NAV represents economic portfolio wealth.

Historical stock splits affect the quoted share price and share count,
but they NEVER affect NAV or portfolio wealth.

For TQQQ, the historical split schedule is loaded from:

    cache/simulatedTQQQ.csv

The CSV's `split` column is authoritative.

No artificial price-band denomination splits are generated.

This module is intended for historical research/backtesting.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

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

    # ==================================================================
    # Historical split schedule
    # ==================================================================

    @staticmethod
    def _split_schedule_path() -> Path:
        """
        Return the repository-level simulated TQQQ CSV path.

        leveraged_provider.py lives at:

            <repo>/marketpilot/data/leveraged_provider.py

        Therefore:

            parents[0] = data
            parents[1] = marketpilot
            parents[2] = repo
        """

        return (
            Path(__file__).resolve().parents[2]
            / "cache"
            / "simulatedTQQQ.csv"
        )

    @classmethod
    def _load_csv_split_schedule(
        cls,
        symbol: str,
    ) -> dict[pd.Timestamp, float]:
        """
        Load historical split factors from the simulated TQQQ CSV.

        The CSV uses:

            split = 2.0   -> 2-for-1 forward split
            split = 0.25  -> 1-for-4 reverse split
            split = 1.0   -> no split

        Splits affect quoted share price only.

        They do NOT affect economic NAV.

        At present the repository contains the authoritative historical
        split schedule for TQQQ in simulatedTQQQ.csv.

        If the requested symbol is not TQQQ, no CSV schedule is applied.
        """

        symbol = symbol.upper()

        if symbol != "TQQQ":
            return {}

        path = cls._split_schedule_path()

        if not path.exists():
            raise FileNotFoundError(
                "Historical TQQQ split schedule was not found at:\n"
                f"    {path}\n"
                "\n"
                "Expected file:\n"
                "    cache/simulatedTQQQ.csv"
            )

        try:
            df = pd.read_csv(path)
        except Exception as exc:
            raise RuntimeError(
                "Unable to read the historical TQQQ split schedule:\n"
                f"    {path}"
            ) from exc

        required = {"date", "split"}

        missing = required.difference(df.columns)

        if missing:
            raise ValueError(
                "Historical TQQQ split CSV is missing required "
                f"columns: {sorted(missing)}"
            )

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        df["split"] = pd.to_numeric(
            df["split"],
            errors="coerce",
        )

        df = df.dropna(
            subset=["date", "split"]
        )

        df = df[
            df["split"] > 0
        ]

        df = df[
            df["split"] != 1.0
        ]

        df = df.sort_values("date")

        schedule: dict[pd.Timestamp, float] = {}

        for row in df.itertuples(index=False):
            date = pd.Timestamp(row.date)
            factor = float(row.split)

            if (
                not math.isfinite(factor)
                or factor <= 0
            ):
                continue

            schedule[date] = factor

        logger.info(
            f"{symbol} historical split schedule loaded: "
            f"{len(schedule)} events"
        )

        for date, factor in schedule.items():
            logger.info(
                f"    {date.date()} : split {factor:g}"
            )

        return schedule

    @classmethod
    def _historical_split_factors(
        cls,
        symbol: str,
    ) -> dict[pd.Timestamp, float]:
        """
        Backwards-compatible wrapper around the CSV-based schedule.

        The historical split schedule is intentionally NOT hard-coded.

        The repository CSV is the source of truth.
        """

        return cls._load_csv_split_schedule(symbol)

    # ==================================================================
    # Split normalization
    # ==================================================================

    @staticmethod
    def _extract_split_series(
        df: pd.DataFrame,
    ) -> pd.Series:
        """
        Extract a split series from a dataframe.

        Supports common Yahoo/yfinance names as well as the CSV naming
        convention used by simulatedTQQQ.csv.
        """

        candidates = [
            "Stock Splits",
            "Split",
            "split",
            "stock_splits",
        ]

        for column in candidates:
            if column not in df.columns:
                continue

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

    # ==================================================================
    # Validation
    # ==================================================================

    def validate_history(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> None:
        """
        Validate a completed leveraged ETF history.
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

    # ==================================================================
    # Synthetic share-price layer
    # ==================================================================

    @staticmethod
    def _build_split_aware_price(
        nav: pd.Series,
        historical_splits: pd.Series,
        target_price: float,
    ) -> tuple[pd.Series, pd.Series, pd.Series]:
        """
        Convert economic NAV into a split-aware synthetic share price.

        NAV is NEVER modified.

        The model maintains a synthetic share count.

        Price:

            price = NAV / shares

        On a forward split:

            shares *= split_factor

        Therefore:

            price /= split_factor

        On a reverse split:

            shares *= 0.25

        Therefore:

            price *= 4

        Total wealth remains:

            shares * price = NAV

        There are NO artificial price-band splits here.

        Returns:

            synthetic_price
            applied_split
            cumulative_split_factor
        """

        if nav.empty:
            empty = pd.Series(
                dtype=float,
                index=nav.index,
            )

            return (
                empty,
                empty,
                empty,
            )

        nav = nav.astype(float)

        historical_splits = (
            historical_splits
            .reindex(nav.index)
            .fillna(1.0)
        )

        first_nav = float(
            nav.iloc[0]
        )

        if (
            not math.isfinite(first_nav)
            or first_nav <= 0
        ):
            raise ValueError(
                "Synthetic NAV begins with an invalid value: "
                f"{first_nav}"
            )

        if (
            not math.isfinite(target_price)
            or target_price <= 0
        ):
            raise ValueError(
                f"Invalid synthetic target price: {target_price}"
            )

        # Start with a share count that makes the first quoted
        # synthetic price equal to target_price.
        shares = (
            first_nav / target_price
        )

        if (
            not math.isfinite(shares)
            or shares <= 0
        ):
            raise ValueError(
                f"Invalid initial synthetic share count: {shares}"
            )

        prices = []
        applied_splits = []
        cumulative_splits = []

        cumulative_split = 1.0

        for date in nav.index:

            nav_value = float(
                nav.loc[date]
            )

            if not math.isfinite(nav_value):
                raise ValueError(
                    f"Synthetic NAV became non-finite "
                    f"on {date}: {nav_value}"
                )

            split_factor = float(
                historical_splits.loc[date]
            )

            if (
                not math.isfinite(split_factor)
                or split_factor <= 0
            ):
                split_factor = 1.0

            # ----------------------------------------------------------
            # Historical split.
            #
            # THIS IS THE ONLY SHARE-COUNT ADJUSTMENT.
            #
            # NAV is untouched.
            # ----------------------------------------------------------

            if not math.isclose(
                split_factor,
                1.0,
            ):
                shares *= split_factor
                cumulative_split *= split_factor

            # ----------------------------------------------------------
            # Calculate quoted synthetic price.
            # ----------------------------------------------------------

            if (
                not math.isfinite(shares)
                or shares <= 0
            ):
                raise ValueError(
                    f"Invalid synthetic share count on {date}: "
                    f"{shares}"
                )

            price = (
                nav_value / shares
            )

            if (
                not math.isfinite(price)
                or price <= 0
            ):
                raise ValueError(
                    f"Synthetic price became invalid on {date}: "
                    f"NAV={nav_value}, shares={shares}, "
                    f"price={price}"
                )

            prices.append(price)
            applied_splits.append(split_factor)
            cumulative_splits.append(cumulative_split)

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

        cumulative_split_series = pd.Series(
            cumulative_splits,
            index=nav.index,
            dtype=float,
        )

        return (
            synthetic_price,
            applied_split_series,
            cumulative_split_series,
        )

    # ==================================================================
    # Main history builder
    # ==================================================================

    def get_history(
        self,
        symbol: str,
        underlying_symbol: str,
        actual_history,
        period: str = "max",
        interval: str = "1d",
    ):
        """
        Build the complete leveraged ETF history.
        """

        # --------------------------------------------------------------
        # Underlying history
        # --------------------------------------------------------------

        underlying = (
            self.underlying_provider.get_history(
                underlying_symbol,
                period=period,
                interval=interval,
            )
        )

        # --------------------------------------------------------------
        # Treasury history
        # --------------------------------------------------------------

        treasury = (
            self.treasury_provider.get_history(
                "TBILL",
                period=period,
                interval=interval,
            )
        )

        underlying_df = underlying.copy()
        actual_df = actual_history.copy()
        treasury_df = treasury.copy()

        # --------------------------------------------------------------
        # Normalize indexes
        # --------------------------------------------------------------

        underlying_df.index = pd.to_datetime(
            underlying_df.index
        )

        actual_df.index = pd.to_datetime(
            actual_df.index
        )

        treasury_df.index = pd.to_datetime(
            treasury_df.index
        )

        underlying_df = (
            underlying_df
            .sort_index()
        )

        actual_df = (
            actual_df
            .sort_index()
        )

        treasury_df = (
            treasury_df
            .sort_index()
        )

        # --------------------------------------------------------------
        # Normalize actual Adj Close
        # --------------------------------------------------------------

        if (
            "Adj Close" not in actual_df.columns
            or actual_df["Adj Close"].isna().all()
        ):
            actual_df["Adj Close"] = (
                actual_df["Close"]
            )

        # --------------------------------------------------------------
        # Determine actual ETF inception.
        # --------------------------------------------------------------

        actual_start = actual_df.index.min()

        # --------------------------------------------------------------
        # Only synthesize the period before the real ETF existed.
        # --------------------------------------------------------------

        synthetic_underlying = underlying_df[
            underlying_df.index < actual_start
        ].copy()

        if synthetic_underlying.empty:
            return actual_df

        # --------------------------------------------------------------
        # Underlying total-return price.
        # --------------------------------------------------------------

        if "Adj Close" in synthetic_underlying.columns:
            underlying_close = (
                synthetic_underlying["Adj Close"]
                .copy()
            )
        else:
            underlying_close = (
                synthetic_underlying["Close"]
                .copy()
            )

        underlying_close = (
            underlying_close
            .dropna()
        )

        underlying_close = (
            underlying_close[
                underlying_close > 0
            ]
        )

        if len(underlying_close) < 2:
            raise ValueError(
                f"Insufficient underlying history "
                f"to synthesize {symbol}."
            )

        # --------------------------------------------------------------
        # Treasury rate.
        # --------------------------------------------------------------

        if "Close" in treasury_df.columns:
            treasury_rate = (
                treasury_df["Close"]
                .copy()
            )
        elif "Adj Close" in treasury_df.columns:
            treasury_rate = (
                treasury_df["Adj Close"]
                .copy()
            )
        else:
            raise ValueError(
                "TBILL history must contain a "
                "Close or Adj Close column."
            )

        # FRED DTB3 is expressed as a percentage.
        #
        # Example:
        #
        #     5.00 -> 0.05
        #
        treasury_rate = (
            treasury_rate / 100.0
        )

        # --------------------------------------------------------------
        # Align financing rate with trading dates.
        # --------------------------------------------------------------

        financing_rate = (
            treasury_rate
            .reindex(underlying_close.index)
            .ffill()
            .bfill()
        )

        # --------------------------------------------------------------
        # Existing synthetic daily return calculation.
        #
        # DO NOT change this yet.
        # --------------------------------------------------------------

        underlying_return = (
            underlying_close
            .pct_change()
            .dropna()
        )

        financing_rate = (
            financing_rate
            .reindex(underlying_return.index)
            .ffill()
            .bfill()
        )

        # --------------------------------------------------------------
        # Annual expense ratio -> daily expense drag.
        # --------------------------------------------------------------

        daily_expense = (
            self.expense_ratio / 252.0
        )

        # --------------------------------------------------------------
        # Approximate financing cost.
        #
        # 2x -> approximately 1x financed exposure
        # 3x -> approximately 2x financed exposure
        # --------------------------------------------------------------

        daily_financing = (
            (self.leverage - 1.0)
            * financing_rate
            / 252.0
        )

        # --------------------------------------------------------------
        # Existing leveraged daily return.
        # --------------------------------------------------------------

        leveraged_return = (
            self.leverage
            * underlying_return
            - daily_financing
            - daily_expense
        )

        # A leveraged ETF cannot lose more than 100% on a single day.
        #
        # Use a very small positive floor rather than allowing an
        # exact -100% return, because an exact -100% would permanently
        # destroy the mathematical NAV.
        leveraged_return = (
            leveraged_return
            .clip(lower=-0.999999)
        )

        # --------------------------------------------------------------
        # Economic NAV.
        #
        # THIS IS THE PORTFOLIO WEALTH LAYER.
        #
        # Splits are deliberately NOT applied here.
        # --------------------------------------------------------------

        nav = (
            1.0
            * (1.0 + leveraged_return)
            .cumprod()
        )

        if nav.empty:
            return actual_df

        # --------------------------------------------------------------
        # Important numerical validation.
        #
        # Do NOT silently replace tiny NAV with 1e-300.
        #
        # A very small NAV can be economically valid.
        #
        # Example:
        #
        #     $100,000 -> $143
        #
        # corresponds to:
        #
        #     NAV = 0.00143
        #
        # That is small, but completely representable by float64.
        # --------------------------------------------------------------

        if not nav.notna().all():
            bad_date = nav.index[
                nav.isna()
            ][0]

            raise ValueError(
                f"Synthetic {symbol} NAV contains NaN "
                f"on {bad_date}."
            )

        if not nav.apply(math.isfinite).all():
            bad_date = nav.index[
                ~nav.apply(math.isfinite)
            ][0]

            raise ValueError(
                f"Synthetic {symbol} NAV contains "
                f"a non-finite value on {bad_date}."
            )

        if (nav <= 0).any():
            bad_date = nav.index[
                nav <= 0
            ][0]

            bad_value = nav.loc[bad_date]

            raise ValueError(
                f"Synthetic {symbol} NAV became "
                f"non-positive on {bad_date}: {bad_value}"
            )

        # --------------------------------------------------------------
        # Load authoritative historical split schedule.
        # --------------------------------------------------------------

        historical_split_map = (
            self._historical_split_factors(
                symbol
            )
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

        # --------------------------------------------------------------
        # Synthetic price denomination.
        #
        # Start the synthetic series around $50.
        #
        # This initial denomination has NO effect on NAV or returns.
        # --------------------------------------------------------------

        synthetic_target_price = 50.0

        (
            synthetic_price,
            applied_splits,
            cumulative_splits,
        ) = self._build_split_aware_price(
            nav=nav,
            historical_splits=historical_splits,
            target_price=synthetic_target_price,
        )

        if synthetic_price.empty:
            return actual_df

        # --------------------------------------------------------------
        # Re-anchor the synthetic price to the real ETF at inception.
        #
        # This is a PRICE scaling operation only.
        #
        # NAV remains untouched.
        # --------------------------------------------------------------

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

        # --------------------------------------------------------------
        # Validate final price layer.
        #
        # We do NOT clip tiny prices upward to an arbitrary value.
        #
        # A very small positive price is valid.
        # --------------------------------------------------------------

        if not synthetic_price.notna().all():
            bad_date = synthetic_price.index[
                synthetic_price.isna()
            ][0]

            raise ValueError(
                f"Synthetic {symbol} price contains "
                f"NaN on {bad_date}"
            )

        if not synthetic_price.apply(
            math.isfinite
        ).all():
            bad_date = synthetic_price.index[
                ~synthetic_price.apply(math.isfinite)
            ][0]

            raise ValueError(
                f"Synthetic {symbol} price contains "
                f"a non-finite value on {bad_date}"
            )

        if (synthetic_price <= 0).any():
            bad_date = synthetic_price.index[
                synthetic_price <= 0
            ][0]

            raise ValueError(
                f"Synthetic {symbol} price became "
                f"non-positive on {bad_date}: "
                f"{synthetic_price.loc[bad_date]}"
            )

        # --------------------------------------------------------------
        # Build synthetic OHLC data.
        #
        # We only have a synthetic close series at this stage.
        # --------------------------------------------------------------

        synthetic_df = pd.DataFrame(
            index=synthetic_price.index
        )

        synthetic_df["Open"] = (
            synthetic_price
        )

        synthetic_df["High"] = (
            synthetic_price
        )

        synthetic_df["Low"] = (
            synthetic_price
        )

        synthetic_df["Close"] = (
            synthetic_price
        )

        synthetic_df["Adj Close"] = (
            synthetic_price
        )

        synthetic_df["NAV"] = nav

        synthetic_df["Split"] = (
            applied_splits
        )

        synthetic_df["Cumulative Split"] = (
            cumulative_splits
        )

        synthetic_df["Volume"] = 0

        # --------------------------------------------------------------
        # Synthetic diagnostics.
        # --------------------------------------------------------------

        synthetic_first_nav = float(
            nav.iloc[0]
        )

        synthetic_last_nav = float(
            nav.iloc[-1]
        )

        synthetic_min_nav = float(
            nav.min()
        )

        synthetic_first_price = float(
            synthetic_price.iloc[0]
        )

        synthetic_last_price = float(
            synthetic_price.iloc[-1]
        )

        synthetic_min_price = float(
            synthetic_price.min()
        )

        synthetic_max_price = float(
            synthetic_price.max()
        )

        split_count = int(
            (
                applied_splits
                != 1.0
            ).sum()
        )

        cumulative_split_final = float(
            cumulative_splits.iloc[-1]
        )

        print(
            f"Synthetic {symbol}:"
        )

        print(
            f"    Synthetic last : "
            f"{nav.index[-1].date()} "
            f"${synthetic_last_price:.6f}"
        )

        print(
            f"    Actual first   : "
            f"{actual_df.index[0].date()} "
            f"${actual_first_close:.6f}"
        )

        print(
            f"    Price ratio    : "
            f"{actual_first_close / synthetic_last_price:.4f}"
        )

        print(
            f"    Synthetic first: "
            f"{nav.index[0].date()} "
            f"${synthetic_first_price:.6f}"
        )

        print(
            f"    Synthetic min  : "
            f"${synthetic_min_price:.12f}"
        )

        print(
            f"    Synthetic max  : "
            f"${synthetic_max_price:.6f}"
        )

        print(
            f"    Synthetic NAV first : "
            f"{synthetic_first_nav:.12g}"
        )

        print(
            f"    Synthetic NAV last  : "
            f"{synthetic_last_nav:.12g}"
        )

        print(
            f"    Synthetic NAV min   : "
            f"{synthetic_min_nav:.12g}"
        )

        print(
            f"    Synthetic splits : "
            f"{split_count}"
        )

        print(
            f"    Cumulative split factor : "
            f"{cumulative_split_final:.12g}"
        )

        # --------------------------------------------------------------
        # Combine synthetic + actual history.
        # --------------------------------------------------------------

        combined = pd.concat(
            [
                synthetic_df,
                actual_df,
            ]
        )

        # Real ETF data wins if a date overlaps.
        combined = (
            combined[
                ~combined.index.duplicated(
                    keep="last"
                )
            ]
            .sort_index()
        )

        # --------------------------------------------------------------
        # History diagnostics.
        # --------------------------------------------------------------

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

        # --------------------------------------------------------------
        # Handoff diagnostics.
        # --------------------------------------------------------------

        handoff_start = (
            actual_df.index.min()
        )

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
                handoff_start
                - pd.Timedelta(days=5):
                handoff_start
                + pd.Timedelta(days=5),
                handoff_columns,
            ].to_string()
        )

        # --------------------------------------------------------------
        # Validate completed price history.
        # --------------------------------------------------------------

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

        return combined