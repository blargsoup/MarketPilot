"""
Synthetic leveraged ETF provider.

This module builds continuous historical leveraged ETF series by combining:

    1. Real ETF history from inception onward.
    2. Synthetic pre-inception history.
    3. A separate economic NAV / wealth layer.
    4. A separate quoted synthetic share-price layer.
    5. Historical split events.

IMPORTANT:

Historical splits NEVER change economic NAV.

A split changes:

    - share count
    - quoted share price

A split does NOT change:

    - portfolio wealth
    - economic NAV
    - investment return

For TQQQ, the repository's simulatedTQQQ.csv is the authoritative
historical synthetic price/reference series.

The CSV also contains the historical split schedule.

No artificial price-band denomination splits are generated.
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
    # Paths
    # ==================================================================

    @staticmethod
    def _split_schedule_path() -> Path:
        """
        Repository-level simulated TQQQ CSV.

        <repo>/
            cache/
                simulatedTQQQ.csv

            marketpilot/
                data/
                    leveraged_provider.py
        """

        return (
            Path(__file__).resolve().parents[2]
            / "cache"
            / "simulatedTQQQ.csv"
        )

    # ==================================================================
    # Historical TQQQ CSV
    # ==================================================================

    @classmethod
    def _load_simulated_tqqq(
        cls,
    ) -> pd.DataFrame:
        """
        Load the repository's simulated TQQQ data.

        This file is treated as the historical reference for the
        pre-inception TQQQ path.

        The split column is metadata describing share-count events.
        """

        path = cls._split_schedule_path()

        if not path.exists():
            raise FileNotFoundError(
                "Historical TQQQ simulation file was not found:\n"
                f"    {path}\n"
                "\n"
                "Expected:\n"
                "    cache/simulatedTQQQ.csv"
            )

        df = pd.read_csv(path)

        required = {
            "date",
            "close",
            "split",
        }

        missing = required.difference(df.columns)

        if missing:
            raise ValueError(
                "simulatedTQQQ.csv is missing required columns: "
                f"{sorted(missing)}"
            )

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        df["close"] = pd.to_numeric(
            df["close"],
            errors="coerce",
        )

        df["split"] = pd.to_numeric(
            df["split"],
            errors="coerce",
        ).fillna(1.0)

        df = df.dropna(
            subset=[
                "date",
                "close",
            ]
        )

        df = df[
            df["close"] > 0
        ]

        df["split"] = df["split"].where(
            df["split"] > 0,
            1.0,
        )

        df = (
            df.sort_values("date")
            .drop_duplicates(
                subset=["date"],
                keep="last",
            )
        )

        df = df.set_index("date")

        logger.info(
            "Loaded simulated TQQQ reference: "
            f"{len(df)} rows, "
            f"{df.index.min().date()} -> "
            f"{df.index.max().date()}"
        )

        return df

    # ==================================================================
    # Historical split schedule
    # ==================================================================

    @classmethod
    def _load_csv_split_schedule(
        cls,
        symbol: str,
    ) -> dict[pd.Timestamp, float]:
        """
        Load historical split factors.

        CSV semantics:

            2.0   = 2-for-1 forward split
            3.0   = 3-for-1 forward split
            0.25  = 1-for-4 reverse split

        Splits affect quoted price/share count only.

        They NEVER modify economic NAV.
        """

        symbol = symbol.upper()

        if symbol != "TQQQ":
            return {}

        df = cls._load_simulated_tqqq()

        schedule: dict[pd.Timestamp, float] = {}

        for date, row in df.iterrows():

            factor = float(
                row["split"]
            )

            if (
                not math.isfinite(factor)
                or factor <= 0
                or math.isclose(
                    factor,
                    1.0,
                )
            ):
                continue

            schedule[pd.Timestamp(date)] = factor

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
        return cls._load_csv_split_schedule(
            symbol
        )

    # ==================================================================
    # Split series
    # ==================================================================

    @classmethod
    def _build_split_series(
        cls,
        symbol: str,
        index: pd.DatetimeIndex,
    ) -> pd.Series:
        """
        Create a split series aligned to the supplied dates.
        """

        splits = pd.Series(
            1.0,
            index=index,
            dtype=float,
        )

        schedule = cls._historical_split_factors(
            symbol
        )

        for date, factor in schedule.items():

            if date in splits.index:
                splits.loc[date] = factor

        return splits

    # ==================================================================
    # Validation
    # ==================================================================

    def validate_history(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> None:

        if df is None or df.empty:
            raise ValueError(
                f"{symbol}: history is empty"
            )

        required = [
            "Open",
            "High",
            "Low",
            "Close",
            "Adj Close",
        ]

        missing = [
            column
            for column in required
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
                f"{symbol}: index must be DatetimeIndex"
            )

        if df.index.has_duplicates:
            raise ValueError(
                f"{symbol}: duplicate dates detected"
            )

        if not df.index.is_monotonic_increasing:
            raise ValueError(
                f"{symbol}: dates are not sorted"
            )

        prices = df[required]

        if prices.isna().any().any():
            raise ValueError(
                f"{symbol}: NaN prices detected"
            )

        for column in required:

            if (
                ~prices[column].apply(
                    math.isfinite
                )
            ).any():
                raise ValueError(
                    f"{symbol}: infinite {column} values"
                )

            if (
                prices[column] <= 0
            ).any():
                bad_date = prices.index[
                    prices[column] <= 0
                ][0]

                raise ValueError(
                    f"{symbol}: non-positive "
                    f"{column} on {bad_date}"
                )

    # ==================================================================
    # Build synthetic TQQQ from repository reference
    # ==================================================================

    @classmethod
    def _build_tqqq_reference_history(
        cls,
        symbol: str,
        actual_start: pd.Timestamp,
        actual_first_close: float,
    ):
        """
        Build the pre-inception TQQQ history from the repository's
        simulated TQQQ reference.

        The CSV is the authoritative historical simulation used to
        prevent the synthetic TQQQ from collapsing numerically due to
        differences between the local QQQ series and the historical
        reconstruction.

        NAV is derived from the synthetic price relative to the
        inception handoff.

        Splits do not alter NAV.
        """

        if symbol.upper() != "TQQQ":
            return None

        reference = cls._load_simulated_tqqq()

        reference = reference[
            reference.index < actual_start
        ].copy()

        if reference.empty:
            return None

        reference_close = (
            reference["close"]
            .astype(float)
        )

        if (
            not reference_close.notna().all()
            or (reference_close <= 0).any()
        ):
            raise ValueError(
                "Invalid values found in simulatedTQQQ.csv"
            )

        # --------------------------------------------------------------
        # The CSV's historical price is already a continuous simulated
        # price series.
        #
        # We normalize it to the real ETF's first closing price.
        #
        # This is a PRICE operation only.
        # --------------------------------------------------------------

        synthetic_last = float(
            reference_close.iloc[-1]
        )

        if (
            not math.isfinite(synthetic_last)
            or synthetic_last <= 0
        ):
            raise ValueError(
                "Invalid final simulated TQQQ reference price"
            )

        price_scale = (
            actual_first_close
            / synthetic_last
        )

        synthetic_price = (
            reference_close
            * price_scale
        )

        # --------------------------------------------------------------
        # Economic NAV.
        #
        # NAV is relative to the actual ETF inception handoff.
        #
        # At the last synthetic date, NAV is exactly 1.0.
        #
        # Therefore an investment of $100,000 held through the synthetic
        # period has wealth:
        #
        #     100000 * NAV
        #
        # immediately before the real ETF begins.
        # --------------------------------------------------------------

        synthetic_nav = (
            reference_close
            / synthetic_last
        )

        # --------------------------------------------------------------
        # Historical split metadata.
        # --------------------------------------------------------------

        split_series = (
            reference["split"]
            .astype(float)
        )

        cumulative_split = (
            split_series
            .cumprod()
        )

        return (
            synthetic_price,
            synthetic_nav,
            split_series,
            cumulative_split,
        )

    # ==================================================================
    # Generic synthetic NAV builder
    # ==================================================================

    def _build_generic_synthetic_nav(
        self,
        underlying_close: pd.Series,
        treasury_rate: pd.Series,
    ):
        """
        Existing daily leveraged-return calculation.

        This remains the generic engine for leveraged ETFs that do not
        have a repository-specific historical reference.

        Economic NAV is independent from splits.
        """

        underlying_return = (
            underlying_close
            .pct_change()
            .dropna()
        )

        financing_rate = (
            treasury_rate
            .reindex(
                underlying_return.index
            )
            .ffill()
            .bfill()
        )

        daily_expense = (
            self.expense_ratio
            / 252.0
        )

        daily_financing = (
            (self.leverage - 1.0)
            * financing_rate
            / 252.0
        )

        leveraged_return = (
            self.leverage
            * underlying_return
            - daily_financing
            - daily_expense
        )

        # Never allow a mathematical return <= -100%.
        #
        # This is only a mathematical protection. It is NOT a split.
        leveraged_return = (
            leveraged_return
            .clip(
                lower=-0.999999
            )
        )

        nav = (
            1.0
            * (1.0 + leveraged_return)
            .cumprod()
        )

        return (
            nav,
            leveraged_return,
        )

    # ==================================================================
    # Generic split-aware price layer
    # ==================================================================

    @staticmethod
    def _build_split_aware_price(
        nav: pd.Series,
        historical_splits: pd.Series,
        target_price: float,
    ):
        """
        Convert economic NAV into a quoted share price.

        NAV is never modified.

        Starting share count is chosen so the first synthetic price
        equals target_price.

        Forward split:

            shares *= split
            price  /= split

        Reverse split:

            shares *= 0.25
            price  /= 0.25

        Therefore:

            shares * price == NAV

        at every point in the series.

        There are NO artificial denomination splits.
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
                f"Invalid first synthetic NAV: "
                f"{first_nav}"
            )

        if (
            not math.isfinite(target_price)
            or target_price <= 0
        ):
            raise ValueError(
                f"Invalid target price: "
                f"{target_price}"
            )

        shares = (
            first_nav
            / target_price
        )

        prices = []
        applied_splits = []
        cumulative_splits = []

        cumulative_split = 1.0

        for date in nav.index:

            nav_value = float(
                nav.loc[date]
            )

            if (
                not math.isfinite(nav_value)
                or nav_value <= 0
            ):
                raise ValueError(
                    f"Invalid NAV on {date}: "
                    f"{nav_value}"
                )

            split_factor = float(
                historical_splits.loc[date]
            )

            if (
                not math.isfinite(
                    split_factor
                )
                or split_factor <= 0
            ):
                split_factor = 1.0

            if not math.isclose(
                split_factor,
                1.0,
            ):
                shares *= split_factor
                cumulative_split *= split_factor

            price = (
                nav_value
                / shares
            )

            if (
                not math.isfinite(price)
                or price <= 0
            ):
                raise ValueError(
                    f"Invalid synthetic price on "
                    f"{date}: {price}"
                )

            prices.append(price)
            applied_splits.append(
                split_factor
            )
            cumulative_splits.append(
                cumulative_split
            )

        return (
            pd.Series(
                prices,
                index=nav.index,
                dtype=float,
            ),
            pd.Series(
                applied_splits,
                index=nav.index,
                dtype=float,
            ),
            pd.Series(
                cumulative_splits,
                index=nav.index,
                dtype=float,
            ),
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

        symbol = symbol.upper()

        # --------------------------------------------------------------
        # Load underlying.
        # --------------------------------------------------------------

        underlying = (
            self.underlying_provider.get_history(
                underlying_symbol,
                period=period,
                interval=interval,
            )
        )

        # --------------------------------------------------------------
        # Load treasury.
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
        # Normalize actual ETF Adj Close.
        #
        # Some Yahoo Finance histories can return a valid OHLC/Close
        # series while Adj Close is entirely NaN. For the leveraged ETF
        # history used by MarketPilot, Close is the authoritative quoted
        # price when adjusted close is unavailable.
        #
        # Fill only missing Adj Close values; never overwrite valid
        # adjusted prices.
        # --------------------------------------------------------------

        if "Adj Close" not in actual_df.columns:
            actual_df["Adj Close"] = actual_df["Close"]
        else:
            actual_df["Adj Close"] = (
                actual_df["Adj Close"]
                .fillna(actual_df["Close"])
            )

        # --------------------------------------------------------------
        # Normalize indexes.
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
        # Actual ETF inception.
        # --------------------------------------------------------------

        actual_start = (
            actual_df.index.min()
        )

        actual_first_close = float(
            actual_df["Close"].iloc[0]
        )

        if (
            not math.isfinite(
                actual_first_close
            )
            or actual_first_close <= 0
        ):
            raise ValueError(
                f"Invalid first actual {symbol} "
                f"close: {actual_first_close}"
            )

        # --------------------------------------------------------------
        # Underlying pre-inception history.
        # --------------------------------------------------------------

        synthetic_underlying = (
            underlying_df[
                underlying_df.index < actual_start
            ].copy()
        )

        if synthetic_underlying.empty:
            return actual_df

        # --------------------------------------------------------------
        # TQQQ special historical reference.
        #
        # This is the critical fix.
        #
        # The repository already contains the simulated TQQQ path.
        # Use that path rather than allowing the generic QQQ-based NAV
        # calculation to collapse to ~1e-148.
        # --------------------------------------------------------------

        if symbol == "TQQQ":

            result = (
                self._build_tqqq_reference_history(
                    symbol=symbol,
                    actual_start=actual_start,
                    actual_first_close=actual_first_close,
                )
            )

            if result is not None:

                (
                    synthetic_price,
                    synthetic_nav,
                    applied_splits,
                    cumulative_splits,
                ) = result

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

                synthetic_df["NAV"] = (
                    synthetic_nav
                )

                synthetic_df["Split"] = (
                    applied_splits
                )

                synthetic_df[
                    "Cumulative Split"
                ] = cumulative_splits

                synthetic_df["Volume"] = 0

                # ------------------------------------------------------
                # Diagnostics.
                # ------------------------------------------------------

                first_nav = float(
                    synthetic_nav.iloc[0]
                )

                last_nav = float(
                    synthetic_nav.iloc[-1]
                )

                min_nav = float(
                    synthetic_nav.min()
                )

                first_price = float(
                    synthetic_price.iloc[0]
                )

                last_price = float(
                    synthetic_price.iloc[-1]
                )

                min_price = float(
                    synthetic_price.min()
                )

                max_price = float(
                    synthetic_price.max()
                )

                split_count = int(
                    (
                        applied_splits
                        != 1.0
                    ).sum()
                )

                cumulative_split = float(
                    cumulative_splits.iloc[-1]
                )

                logger.info(
                    "TQQQ synthetic reference model"
                )

                print(
                    "Synthetic TQQQ:"
                )

                print(
                    f"    Synthetic last : "
                    f"{synthetic_price.index[-1].date()} "
                    f"${last_price:.6f}"
                )

                print(
                    f"    Actual first   : "
                    f"{actual_start.date()} "
                    f"${actual_first_close:.6f}"
                )

                print(f"    Price ratio    : {actual_first_close / float(result[0].iloc[-1]):.4f}")

                print(
                    f"    Synthetic first: "
                    f"{synthetic_price.index[0].date()} "
                    f"${first_price:.6f}"
                )

                print(
                    f"    Synthetic min  : "
                    f"${min_price:.12f}"
                )

                print(
                    f"    Synthetic max  : "
                    f"${max_price:.6f}"
                )

                print(
                    f"    Synthetic NAV first : "
                    f"{first_nav:.12g}"
                )

                print(
                    f"    Synthetic NAV last  : "
                    f"{last_nav:.12g}"
                )

                print(
                    f"    Synthetic NAV min   : "
                    f"{min_nav:.12g}"
                )

                print(
                    f"    Synthetic splits : "
                    f"{split_count}"
                )

                print(
                    f"    Cumulative split factor : "
                    f"{cumulative_split:.12g}"
                )

                # ------------------------------------------------------
                # Combine.
                # ------------------------------------------------------

                combined = pd.concat(
                    [
                        synthetic_df,
                        actual_df,
                    ]
                )

                combined = (
                    combined[
                        ~combined.index.duplicated(
                            keep="last"
                        )
                    ]
                    .sort_index()
                )

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

                logger.info(
                    f"{symbol} history validation: "
                    f"{len(combined)} rows, "
                    f"{combined.index.min().date()} "
                    f"-> "
                    f"{combined.index.max().date()}"
                )

                logger.info(
                    f"{symbol} actual history: "
                    f"{len(actual_df)} rows, "
                    f"{actual_df.index.min().date()} "
                    f"-> "
                    f"{actual_df.index.max().date()}"
                )

                logger.info(
                    f"{symbol} synthetic history: "
                    f"{len(synthetic_df)} rows, "
                    f"{synthetic_df.index.min().date()} "
                    f"-> "
                    f"{synthetic_df.index.max().date()}"
                )

                handoff_columns = [
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Adj Close",
                ]

                logger.info(
                    f"{symbol} handoff window:"
                )

                logger.info(
                    "\n"
                    +
                    combined.loc[
                        actual_start
                        - pd.Timedelta(days=5):
                        actual_start
                        + pd.Timedelta(days=5),
                        handoff_columns,
                    ].to_string()
                )

                return combined

        # ==============================================================
        # Generic leveraged ETF synthesis
        # ==============================================================

        if (
            "Adj Close"
            in synthetic_underlying.columns
        ):
            underlying_close = (
                synthetic_underlying[
                    "Adj Close"
                ]
                .copy()
            )
        else:
            underlying_close = (
                synthetic_underlying[
                    "Close"
                ]
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
                f"to synthesize {symbol}"
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
                "TBILL history must contain "
                "Close or Adj Close."
            )

        treasury_rate = (
            treasury_rate
            / 100.0
        )

        # --------------------------------------------------------------
        # Build generic NAV.
        # --------------------------------------------------------------

        nav, leveraged_return = (
            self._build_generic_synthetic_nav(
                underlying_close=underlying_close,
                treasury_rate=treasury_rate,
            )
        )

        if nav.empty:
            return actual_df

        if not nav.notna().all():
            raise ValueError(
                f"Synthetic {symbol} NAV "
                "contains NaN values."
            )

        if not nav.apply(
            math.isfinite
        ).all():
            raise ValueError(
                f"Synthetic {symbol} NAV "
                "contains non-finite values."
            )

        if (nav <= 0).any():
            bad_date = nav.index[
                nav <= 0
            ][0]

            raise ValueError(
                f"Synthetic {symbol} NAV became "
                f"non-positive on {bad_date}"
            )

        # --------------------------------------------------------------
        # Split layer.
        #
        # This is deliberately AFTER NAV construction.
        #
        # Splits cannot affect NAV.
        # --------------------------------------------------------------

        historical_splits = (
            self._build_split_series(
                symbol,
                nav.index,
            )
        )

        # --------------------------------------------------------------
        # Generic initial denomination.
        #
        # This is NOT a price-band mechanism.
        #
        # It is simply the arbitrary initial share denomination.
        # --------------------------------------------------------------

        target_price = 50.0

        (
            synthetic_price,
            applied_splits,
            cumulative_splits,
        ) = self._build_split_aware_price(
            nav=nav,
            historical_splits=historical_splits,
            target_price=target_price,
        )

        # --------------------------------------------------------------
        # Re-anchor price to actual ETF inception.
        #
        # NAV remains untouched.
        # --------------------------------------------------------------

        synthetic_last_price = float(
            synthetic_price.iloc[-1]
        )

        if (
            not math.isfinite(
                synthetic_last_price
            )
            or synthetic_last_price <= 0
        ):
            raise ValueError(
                f"Invalid final synthetic "
                f"{symbol} price"
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
        # Build OHLC.
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

        synthetic_df[
            "Cumulative Split"
        ] = cumulative_splits

        synthetic_df["Volume"] = 0

        # --------------------------------------------------------------
        # Diagnostics.
        # --------------------------------------------------------------

        first_nav = float(
            nav.iloc[0]
        )

        last_nav = float(
            nav.iloc[-1]
        )

        min_nav = float(
            nav.min()
        )

        first_price = float(
            synthetic_price.iloc[0]
        )

        last_price = float(
            synthetic_price.iloc[-1]
        )

        min_price = float(
            synthetic_price.min()
        )

        max_price = float(
            synthetic_price.max()
        )

        split_count = int(
            (
                applied_splits
                != 1.0
            ).sum()
        )

        cumulative_split = float(
            cumulative_splits.iloc[-1]
        )

        print(
            f"Synthetic {symbol}:"
        )

        print(
            f"    Synthetic last : "
            f"{nav.index[-1].date()} "
            f"${last_price:.6f}"
        )

        print(
            f"    Actual first   : "
            f"{actual_start.date()} "
            f"${actual_first_close:.6f}"
        )

        print(f"    Price ratio    : {actual_first_close / last_price:.4f}")

        print(
            f"    Synthetic first: "
            f"{nav.index[0].date()} "
            f"${first_price:.6f}"
        )

        print(
            f"    Synthetic min  : "
            f"${min_price:.12f}"
        )

        print(
            f"    Synthetic max  : "
            f"${max_price:.6f}"
        )

        print(
            f"    Synthetic NAV first : "
            f"{first_nav:.12g}"
        )

        print(
            f"    Synthetic NAV last  : "
            f"{last_nav:.12g}"
        )

        print(
            f"    Synthetic NAV min   : "
            f"{min_nav:.12g}"
        )

        print(
            f"    Synthetic splits : "
            f"{split_count}"
        )

        print(
            f"    Cumulative split factor : "
            f"{cumulative_split:.12g}"
        )

        # --------------------------------------------------------------
        # Combine synthetic + actual.
        # --------------------------------------------------------------

        combined = pd.concat(
            [
                synthetic_df,
                actual_df,
            ]
        )

        combined = (
            combined[
                ~combined.index.duplicated(
                    keep="last"
                )
            ]
            .sort_index()
        )

        # --------------------------------------------------------------
        # Diagnostics.
        # --------------------------------------------------------------

        logger.info(
            f"{symbol} history validation: "
            f"{len(combined)} rows, "
            f"{combined.index.min().date()} "
            f"-> "
            f"{combined.index.max().date()}"
        )

        logger.info(
            f"{symbol} actual history: "
            f"{len(actual_df)} rows, "
            f"{actual_df.index.min().date()} "
            f"-> "
            f"{actual_df.index.max().date()}"
        )

        logger.info(
            f"{symbol} synthetic history: "
            f"{len(synthetic_df)} rows, "
            f"{synthetic_df.index.min().date()} "
            f"-> "
            f"{synthetic_df.index.max().date()}"
        )

        # --------------------------------------------------------------
        # Handoff window.
        # --------------------------------------------------------------

        handoff_columns = [
            "Open",
            "High",
            "Low",
            "Close",
            "Adj Close",
        ]

        logger.info(
            f"{symbol} handoff window:"
        )

        logger.info(
            "\n"
            +
            combined.loc[
                actual_start
                - pd.Timedelta(days=5):
                actual_start
                + pd.Timedelta(days=5),
                handoff_columns,
            ].to_string()
        )

        # --------------------------------------------------------------
        # Validate.
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