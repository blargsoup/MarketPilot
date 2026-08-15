"""
Synthetic leveraged ETF provider.

This module coordinates the construction of continuous leveraged ETF
histories.

Responsibilities are intentionally kept small:

    - Load underlying history.
    - Load treasury history.
    - Load actual ETF history.
    - Build special historical references such as TQQQ.
    - Build generic synthetic leveraged NAV.
    - Apply historical/synthetic split schedules.
    - Combine synthetic and actual history.
    - Validate the resulting history.

The actual implementation of those pieces lives in:

    leveraged_reference.py
    leveraged_splits.py
    leveraged_synthetic.py
    leveraged_validation.py
"""

from __future__ import annotations

import logging
import math

import pandas as pd

from .leveraged_reference import (
    LeveragedReferenceBuilder,
)

from .leveraged_splits import (
    LeveragedSplitManager,
)

from .leveraged_synthetic import (
    LeveragedSyntheticBuilder,
)

from .leveraged_validation import (
    LeveragedHistoryValidator,
)


logger = logging.getLogger(__name__)


class LeveragedETFProvider:

    def __init__(
        self,
        underlying_provider,
        treasury_provider,
        leverage: float,
        expense_ratio: float,
    ):
        self.underlying_provider = (
            underlying_provider
        )

        self.treasury_provider = (
            treasury_provider
        )

        self.leverage = leverage
        self.expense_ratio = expense_ratio

        # --------------------------------------------------------------
        # Generic synthetic ETF calculation engine.
        # --------------------------------------------------------------

        self.synthetic_builder = (
            LeveragedSyntheticBuilder(
                leverage=leverage,
                expense_ratio=expense_ratio,
            )
        )

    # ==================================================================
    # History validation
    # ==================================================================

    def validate_history(
        self,
        df: pd.DataFrame,
        symbol: str,
    ) -> None:
        """
        Backwards-compatible wrapper around the new validation module.

        Existing callers can continue using:

            provider.validate_history(...)
        """

        LeveragedHistoryValidator.validate(
            df,
            symbol,
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

        The result consists of:

            synthetic pre-inception history
            +
            actual ETF history

        TQQQ uses the repository-specific simulatedTQQQ.csv reference.

        All other leveraged ETFs use the generic leveraged NAV model.
        """

        symbol = symbol.upper()

        # ==============================================================
        # 1. Load underlying history
        # ==============================================================

        underlying = (
            self.underlying_provider.get_history(
                underlying_symbol,
                period=period,
                interval=interval,
            )
        )

        # ==============================================================
        # 2. Load treasury history
        # ==============================================================

        treasury = (
            self.treasury_provider.get_history(
                "TBILL",
                period=period,
                interval=interval,
            )
        )

        # ==============================================================
        # 3. Copy inputs
        # ==============================================================

        underlying_df = (
            underlying.copy()
        )

        actual_df = (
            actual_history.copy()
        )

        treasury_df = (
            treasury.copy()
        )

        # ==============================================================
        # 4. Normalize actual ETF Adj Close
        # ==============================================================

        if "Adj Close" not in actual_df.columns:

            actual_df["Adj Close"] = (
                actual_df["Close"]
            )

        else:

            actual_df["Adj Close"] = (
                actual_df["Adj Close"]
                .fillna(
                    actual_df["Close"]
                )
            )

        # ==============================================================
        # 5. Normalize indexes
        # ==============================================================

        underlying_df.index = (
            pd.to_datetime(
                underlying_df.index
            )
        )

        actual_df.index = (
            pd.to_datetime(
                actual_df.index
            )
        )

        treasury_df.index = (
            pd.to_datetime(
                treasury_df.index
            )
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

        # ==============================================================
        # 6. Determine actual ETF inception
        # ==============================================================

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

        # ==============================================================
        # 7. Find underlying history before ETF inception
        # ==============================================================

        synthetic_underlying = (
            underlying_df[
                underlying_df.index
                < actual_start
            ].copy()
        )

        if synthetic_underlying.empty:

            logger.warning(
                f"{symbol}: no underlying history "
                "exists before ETF inception. "
                "Returning actual history only."
            )

            return actual_df

        # ==============================================================
        # 8. SPECIAL TQQQ REFERENCE MODEL
        # ==============================================================
        #
        # TQQQ has a repository-specific historical reconstruction
        # stored in:
        #
        #     cache/simulatedTQQQ.csv
        #
        # This is deliberately kept separate from the generic
        # leveraged NAV calculation.
        #
        # ==============================================================
        
        if symbol == "TQQQ":

            result = (
                LeveragedReferenceBuilder
                .build_tqqq(
                    actual_start=actual_start,
                    actual_first_close=(
                        actual_first_close
                    ),
                )
            )

            if result is not None:

                (
                    synthetic_price,
                    synthetic_nav,
                    applied_splits,
                    cumulative_splits,
                ) = result

                synthetic_df = (
                    self._build_reference_dataframe(
                        synthetic_price=(
                            synthetic_price
                        ),
                        synthetic_nav=(
                            synthetic_nav
                        ),
                        applied_splits=(
                            applied_splits
                        ),
                        cumulative_splits=(
                            cumulative_splits
                        ),
                    )
                )

                self._log_reference_diagnostics(
                    symbol=symbol,
                    synthetic_df=synthetic_df,
                    actual_start=actual_start,
                    actual_first_close=(
                        actual_first_close
                    ),
                    actual_df=actual_df,
                )

                return (
                    self._combine_history(
                        synthetic_df,
                        actual_df,
                    )
                )

        # ==============================================================
        # 9. GENERIC LEVERAGED ETF MODEL
        # ==============================================================

        # --------------------------------------------------------------
        # Select underlying price series.
        # --------------------------------------------------------------

        # --------------------------------------------------------------
        # Underlying price series.
        #
        # Keep both Close and Adj Close available.
        #
        # The production model will continue using the selected
        # underlying_close series below.
        #
        # The diagnostic compares both series.
        # --------------------------------------------------------------

        underlying_close = (
            synthetic_underlying[
                "Close"
            ]
            .copy()
        )

        underlying_adj_close = None

        if "Adj Close" in synthetic_underlying.columns:

            underlying_adj_close = (
                synthetic_underlying[
                    "Adj Close"
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

        if underlying_adj_close is not None:

            underlying_adj_close = (
                underlying_adj_close
                .reindex(
                    underlying_close.index
                )
            )

            underlying_adj_close = (
                underlying_adj_close
                .dropna()
            )

            underlying_adj_close = (
                underlying_adj_close[
                    underlying_adj_close > 0
                ]
            )

        if len(underlying_close) < 2:

            raise ValueError(
                f"Insufficient underlying history "
                f"to synthesize {symbol}"
            )

        else:

            underlying_close = (
                synthetic_underlying[
                    "Close"
                ].copy()
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

        # --------------------------------------------------------------
        # Treasury rate.
        # --------------------------------------------------------------
        #
        # The FRED TBILL provider returns annual Treasury rates in
        # percentage-point form.
        #
        # Example:
        #
        #     5.25  ->  5.25%
        #
        # Convert exactly once here into decimal annual form:
        #
        #     5.25  ->  0.0525
        #
        # The leveraged synthetic engine expects decimal rates and
        # therefore must NOT perform another conversion.
        # --------------------------------------------------------------

        if "Close" in treasury_df.columns:
            treasury_rate = treasury_df["Close"].copy()

        elif "Adj Close" in treasury_df.columns:
            treasury_rate = treasury_df["Adj Close"].copy()

        else:
            raise ValueError(
                "TBILL history must contain "
                "Close or Adj Close."
            )

        treasury_rate = pd.to_numeric(
            treasury_rate,
            errors="coerce",
        )

        treasury_rate = (
            treasury_rate
            .ffill()
            .bfill()
        )

        if treasury_rate.empty:
            raise ValueError(
                "TBILL history is empty."
            )

        if treasury_rate.isna().any():
            raise ValueError(
                "TBILL history contains NaN values "
                "after filling."
            )

        if symbol == "QLD":
            self.synthetic_builder.diagnose_against_actual(
                underlying_close=underlying_df["Close"],
                treasury_rate=treasury_rate,
                actual_history=actual_df,
                symbol=symbol,
            )




        # ==============================================================
        # 10. Build generic leveraged NAV
        # ==============================================================

        # --------------------------------------------------------------
        # Leveraged model diagnostics.
        #
        # This compares QQQ Close vs Adj Close, verifies daily returns,
        # verifies Treasury financing, and calculates theoretical 2x NAV.
        # --------------------------------------------------------------

        if symbol == "QLD":

            self.synthetic_builder.diagnose(
                underlying_close=(
                    underlying_close
                ),
                underlying_adj_close=(
                    underlying_adj_close
                ),
                treasury_rate=(
                    treasury_rate
                ),
                symbol=symbol,
            )


        (
            nav,
            leveraged_return,
        ) = (
            self.synthetic_builder.build_nav(
                underlying_close=(
                    underlying_close
                ),
                treasury_rate=(
                    treasury_rate
                ),
            )
        )

        if nav.empty:
            return actual_df

        # ==============================================================
        # 11. Validate NAV
        # ==============================================================

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

        # ==============================================================
        # 12. Build historical split series
        # ==============================================================

        historical_splits = (
            LeveragedSplitManager
            .build_series(
                symbol=symbol,
                index=nav.index,
            )
        )

        # ==============================================================
        # 13. Build split-aware quoted price
        # ==============================================================
        #
        # IMPORTANT:
        #
        # Splits operate on the quoted share-price layer.
        #
        # They do NOT modify NAV.
        #
        # The initial $50 denomination is simply the starting share
        # denomination for the synthetic instrument.
        #
        # ==============================================================

        target_price = 50.0

        (
            synthetic_price,
            applied_splits,
            cumulative_splits,
        ) = (
            self.synthetic_builder
            .build_split_aware_price(
                nav=nav,
                historical_splits=(
                    historical_splits
                ),
                target_price=target_price,
            )
        )

        # ==============================================================
        # 14. Re-anchor synthetic price to actual ETF inception
        # ==============================================================

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

        # ==============================================================
        # 15. Build synthetic DataFrame
        # ==============================================================

        synthetic_df = (
            self._build_generic_dataframe(
                synthetic_price=(
                    synthetic_price
                ),
                nav=nav,
                applied_splits=(
                    applied_splits
                ),
                cumulative_splits=(
                    cumulative_splits
                ),
            )
        )

        # ==============================================================
        # 16. Diagnostics
        # ==============================================================

        self._log_generic_diagnostics(
            symbol=symbol,
            synthetic_df=synthetic_df,
            actual_start=actual_start,
            actual_first_close=(
                actual_first_close
            ),
            actual_df=actual_df,
        )

        # ==============================================================
        # 17. Combine synthetic + actual
        # ==============================================================

        combined = (
            self._combine_history(
                synthetic_df,
                actual_df,
            )
        )

        # ==============================================================
        # 18. Final validation
        # ==============================================================

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

    # ==================================================================
    # Reference DataFrame
    # ==================================================================

    @staticmethod
    def _build_reference_dataframe(
        synthetic_price: pd.Series,
        synthetic_nav: pd.Series,
        applied_splits: pd.Series,
        cumulative_splits: pd.Series,
    ) -> pd.DataFrame:
        """
        Build OHLC-style DataFrame from a repository reference model.
        """

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

        return synthetic_df

    # ==================================================================
    # Generic DataFrame
    # ==================================================================

    @staticmethod
    def _build_generic_dataframe(
        synthetic_price: pd.Series,
        nav: pd.Series,
        applied_splits: pd.Series,
        cumulative_splits: pd.Series,
    ) -> pd.DataFrame:
        """
        Build OHLC-style DataFrame from the generic synthetic model.
        """

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

        return synthetic_df

    # ==================================================================
    # Combine histories
    # ==================================================================

    def _combine_history(
        self,
        synthetic_df: pd.DataFrame,
        actual_df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Combine synthetic pre-inception history with actual history.
        """

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

        return combined

    # ==================================================================
    # Generic diagnostics
    # ==================================================================

    @staticmethod
    def _log_generic_diagnostics(
        symbol: str,
        synthetic_df: pd.DataFrame,
        actual_start: pd.Timestamp,
        actual_first_close: float,
        actual_df: pd.DataFrame,
    ) -> None:

        nav = synthetic_df["NAV"]
        price = synthetic_df["Close"]
        splits = synthetic_df["Split"]
        cumulative = synthetic_df[
            "Cumulative Split"
        ]

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
            price.iloc[0]
        )

        last_price = float(
            price.iloc[-1]
        )

        min_price = float(
            price.min()
        )

        max_price = float(
            price.max()
        )

        split_count = int(
            (
                splits != 1.0
            ).sum()
        )

        cumulative_split = float(
            cumulative.iloc[-1]
        )

        logger.info(
            f"Synthetic {symbol}:"
        )

        logger.info(
            f"    Synthetic last : "
            f"{price.index[-1].date()} "
            f"${last_price:.6f}"
        )

        logger.info(
            f"    Actual first   : "
            f"{actual_start.date()} "
            f"${actual_first_close:.6f}"
        )

        logger.info(
            f"    Price ratio    : "
            f"{actual_first_close / last_price:.4f}"
        )

        logger.info(
            f"    Synthetic first: "
            f"{price.index[0].date()} "
            f"${first_price:.6f}"
        )

        logger.info(
            f"    Synthetic min  : "
            f"${min_price:.12f}"
        )

        logger.info(
            f"    Synthetic max  : "
            f"${max_price:.6f}"
        )

        logger.info(
            f"    Synthetic NAV first : "
            f"{first_nav:.12g}"
        )

        logger.info(
            f"    Synthetic NAV last  : "
            f"{last_nav:.12g}"
        )

        logger.info(
            f"    Synthetic NAV min   : "
            f"{min_nav:.12g}"
        )

        logger.info(
            f"    Synthetic splits : "
            f"{split_count}"
        )

        logger.info(
            f"    Cumulative split factor : "
            f"{cumulative_split:.12g}"
        )

        logger.info(
            f"{symbol} history validation: "
            f"{len(synthetic_df) + len(actual_df)} "
            f"rows"
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

        logger.info(
            f"{symbol} handoff window:"
        )

        logger.info(
            "\n"
            +
            pd.concat(
                [
                    synthetic_df,
                    actual_df,
                ]
            ).loc[
                actual_start
                - pd.Timedelta(days=5):
                actual_start
                + pd.Timedelta(days=5),
                [
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Adj Close",
                ],
            ].to_string()
        )

    # ==================================================================
    # TQQQ diagnostics
    # ==================================================================

    @staticmethod
    def _log_reference_diagnostics(
        symbol: str,
        synthetic_df: pd.DataFrame,
        actual_start: pd.Timestamp,
        actual_first_close: float,
        actual_df: pd.DataFrame,
    ) -> None:

        price = synthetic_df["Close"]
        nav = synthetic_df["NAV"]
        splits = synthetic_df["Split"]
        cumulative = synthetic_df[
            "Cumulative Split"
        ]

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
            price.iloc[0]
        )

        last_price = float(
            price.iloc[-1]
        )

        min_price = float(
            price.min()
        )

        max_price = float(
            price.max()
        )

        split_count = int(
            (
                splits != 1.0
            ).sum()
        )

        cumulative_split = float(
            cumulative.iloc[-1]
        )

        logger.info(
            "TQQQ synthetic reference model"
        )

        print(
            "Synthetic TQQQ:"
        )

        print(
            f"    Synthetic last : "
            f"{price.index[-1].date()} "
            f"${last_price:.6f}"
        )

        print(
            f"    Actual first   : "
            f"{actual_start.date()} "
            f"${actual_first_close:.6f}"
        )

        print(
            f"    Price ratio    : "
            f"{actual_first_close / last_price:.4f}"
        )

        print(
            f"    Synthetic first: "
            f"{price.index[0].date()} "
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

        combined_for_log = pd.concat(
            [
                synthetic_df,
                actual_df,
            ]
        ).sort_index()

        logger.info(
            f"{symbol} history validation: "
            f"{len(combined_for_log)} rows, "
            f"{combined_for_log.index.min().date()} "
            f"-> "
            f"{combined_for_log.index.max().date()}"
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

        logger.info(
            f"{symbol} handoff window:"
        )

        logger.info(
            "\n"
            +
            combined_for_log.loc[
                actual_start
                - pd.Timedelta(days=5):
                actual_start
                + pd.Timedelta(days=5),
                [
                    "Open",
                    "High",
                    "Low",
                    "Close",
                    "Adj Close",
                ],
            ].to_string()
        )

        LeveragedHistoryValidator.validate(
            combined_for_log[
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