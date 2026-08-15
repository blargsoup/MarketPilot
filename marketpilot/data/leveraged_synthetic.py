"""
Generic synthetic leveraged ETF construction.

This module is responsible for:

    1. Daily leveraged return calculation.
    2. Economic NAV construction.
    3. Split-aware quoted share-price construction.
    4. Diagnostic analysis of the underlying return model.

IMPORTANT:

    Economic NAV is independent of stock splits.

    Splits are applied only when constructing the quoted synthetic
    share-price layer.
"""

from __future__ import annotations

import logging
import math

import pandas as pd


logger = logging.getLogger(__name__)


class LeveragedSyntheticBuilder:

    def __init__(
        self,
        leverage: float,
        expense_ratio: float,
    ):

        self.leverage = leverage
        self.expense_ratio = expense_ratio

    # ==================================================================
    # Diagnostic analysis
    # ==================================================================

    def diagnose(
        self,
        underlying_close: pd.Series,
        underlying_adj_close: pd.Series | None,
        treasury_rate: pd.Series,
        symbol: str,
    ) -> None:
        """
        Diagnose the generic leveraged ETF model.

        This method DOES NOT change the production NAV.

        It compares:

            - QQQ Close
            - QQQ Adj Close
            - daily returns
            - theoretical 2x Close NAV
            - theoretical 2x Adj Close NAV
            - financing drag
            - expense drag
            - full leveraged model

        The goal is to determine why a synthetic leveraged ETF
        may collapse during the pre-inception period.
        """

        logger.info("")
        logger.info(
            "=================================================="
        )
        logger.info(
            f"LEVERAGED SYNTHETIC DIAGNOSTICS: {symbol}"
        )
        logger.info(
            "=================================================="
        )

        # --------------------------------------------------------------
        # Normalize Close.
        # --------------------------------------------------------------

        close = (
            underlying_close
            .astype(float)
            .dropna()
        )

        close = close[
            close > 0
        ]

        # --------------------------------------------------------------
        # Normalize Adj Close.
        # --------------------------------------------------------------

        if underlying_adj_close is not None:

            adj_close = (
                underlying_adj_close
                .astype(float)
                .reindex(close.index)
                .dropna()
            )

            adj_close = adj_close[
                adj_close > 0
            ]

        else:

            adj_close = None

        # --------------------------------------------------------------
        # Normalize treasury.
        #
        # IMPORTANT:
        #
        # The provider passes the FRED rate as a decimal
        # (for example 0.0525 = 5.25%).
        # --------------------------------------------------------------

        treasury = (
            treasury_rate
            .astype(float)
            .reindex(close.index)
            .ffill()
            .bfill()
        )

        # ==============================================================
        # 1. UNDERLYING DATA
        # ==============================================================

        logger.info("")
        logger.info(
            "QQQ PRICE DATA"
        )
        logger.info(
            "--------------------------------------------------"
        )

        logger.info(
            f"Rows              : {len(close)}"
        )

        logger.info(
            f"First date        : "
            f"{close.index.min().date()}"
        )

        logger.info(
            f"Last date         : "
            f"{close.index.max().date()}"
        )

        logger.info(
            f"First Close       : "
            f"{close.iloc[0]:.10f}"
        )

        logger.info(
            f"Last Close        : "
            f"{close.iloc[-1]:.10f}"
        )

        logger.info(
            f"Minimum Close     : "
            f"{close.min():.10f}"
        )

        logger.info(
            f"Maximum Close     : "
            f"{close.max():.10f}"
        )

        if adj_close is not None:

            logger.info(
                f"First Adj Close   : "
                f"{adj_close.iloc[0]:.10f}"
            )

            logger.info(
                f"Last Adj Close    : "
                f"{adj_close.iloc[-1]:.10f}"
            )

            logger.info(
                f"Minimum Adj Close : "
                f"{adj_close.min():.10f}"
            )

            logger.info(
                f"Maximum Adj Close : "
                f"{adj_close.max():.10f}"
            )

        # ==============================================================
        # 2. CLOSE VS ADJ CLOSE
        # ==============================================================

        if adj_close is not None:

            comparison = pd.concat(
                [
                    close.rename("Close"),
                    adj_close.rename(
                        "Adj Close"
                    ),
                ],
                axis=1,
            ).dropna()

            comparison[
                "Adj/Close"
            ] = (
                comparison["Adj Close"]
                / comparison["Close"]
            )

            logger.info("")
            logger.info(
                "QQQ CLOSE vs ADJ CLOSE"
            )
            logger.info(
                "--------------------------------------------------"
            )

            logger.info(
                f"First Adj/Close ratio : "
                f"{comparison['Adj/Close'].iloc[0]:.10f}"
            )

            logger.info(
                f"Last Adj/Close ratio  : "
                f"{comparison['Adj/Close'].iloc[-1]:.10f}"
            )

            logger.info(
                f"Minimum ratio         : "
                f"{comparison['Adj/Close'].min():.10f}"
            )

            logger.info(
                f"Maximum ratio         : "
                f"{comparison['Adj/Close'].max():.10f}"
            )

            # ----------------------------------------------------------
            # Show the largest Close vs Adj Close divergences.
            # ----------------------------------------------------------

            comparison[
                "Difference %"
            ] = (
                (
                    comparison["Adj/Close"]
                    - 1.0
                )
                * 100.0
            )

            largest = (
                comparison[
                    "Difference %"
                ]
                .abs()
                .sort_values(
                    ascending=False
                )
                .head(10)
            )

            logger.info("")
            logger.info(
                "Largest Close/Adj Close differences:"
            )

            for date in largest.index:

                row = comparison.loc[
                    date
                ]

                logger.info(
                    f"    {date.date()} | "
                    f"Close={row['Close']:.8f} | "
                    f"Adj={row['Adj Close']:.8f} | "
                    f"Difference="
                    f"{row['Difference %']:.6f}%"
                )

        # ==============================================================
        # 3. DAILY RETURNS
        # ==============================================================

        close_return = (
            close
            .pct_change()
            .dropna()
        )

        if adj_close is not None:

            adj_return = (
                adj_close
                .pct_change()
                .dropna()
            )

        else:

            adj_return = None

        logger.info("")
        logger.info(
            "DAILY RETURN DIAGNOSTICS"
        )
        logger.info(
            "--------------------------------------------------"
        )

        logger.info(
            f"Close first return : "
            f"{close_return.iloc[0] * 100:.8f}%"
        )

        logger.info(
            f"Close worst return : "
            f"{close_return.min() * 100:.8f}%"
        )

        logger.info(
            f"Close best return  : "
            f"{close_return.max() * 100:.8f}%"
        )

        logger.info(
            f"Close mean return  : "
            f"{close_return.mean() * 100:.8f}%"
        )

        if adj_return is not None:

            logger.info(
                f"Adj first return   : "
                f"{adj_return.iloc[0] * 100:.8f}%"
            )

            logger.info(
                f"Adj worst return   : "
                f"{adj_return.min() * 100:.8f}%"
            )

            logger.info(
                f"Adj best return    : "
                f"{adj_return.max() * 100:.8f}%"
            )

            logger.info(
                f"Adj mean return    : "
                f"{adj_return.mean() * 100:.8f}%"
            )

        # ==============================================================
        # 4. THEORETICAL 2x CLOSE NAV
        # ==============================================================

        theoretical_close_return = (
            2.0 * close_return
        )

        theoretical_2x_close_nav = (
            (
                1.0
                + theoretical_close_return
            )
            .clip(
                lower=-0.999999
            )
            .cumprod()
        )

        logger.info("")
        logger.info(
            "THEORETICAL 2x QQQ CLOSE-RETURN NAV"
        )
        logger.info(
            "--------------------------------------------------"
        )

        logger.info(
            f"First NAV : "
            f"{theoretical_2x_close_nav.iloc[0]:.12g}"
        )

        logger.info(
            f"Last NAV  : "
            f"{theoretical_2x_close_nav.iloc[-1]:.12g}"
        )

        logger.info(
            f"Minimum NAV : "
            f"{theoretical_2x_close_nav.min():.12g}"
        )

        # ==============================================================
        # 5. THEORETICAL 2x ADJ CLOSE NAV
        # ==============================================================

        theoretical_2x_adj_nav = None

        if adj_return is not None:

            theoretical_2x_adj_nav = (
                (
                    1.0
                    + 2.0 * adj_return
                )
                .clip(
                    lower=-0.999999
                )
                .cumprod()
            )

            logger.info("")
            logger.info(
                "THEORETICAL 2x QQQ ADJ-CLOSE NAV"
            )
            logger.info(
                "--------------------------------------------------"
            )

            logger.info(
                f"First NAV : "
                f"{theoretical_2x_adj_nav.iloc[0]:.12g}"
            )

            logger.info(
                f"Last NAV  : "
                f"{theoretical_2x_adj_nav.iloc[-1]:.12g}"
            )

            logger.info(
                f"Minimum NAV : "
                f"{theoretical_2x_adj_nav.min():.12g}"
            )

        # ==============================================================
        # 6. TREASURY FINANCING
        # ==============================================================

        daily_expense = (
            self.expense_ratio
            / 252.0
        )

        daily_financing = (
            (self.leverage - 1.0)
            * treasury
            / 252.0
        )

        logger.info("")
        logger.info(
            "TREASURY FINANCING DIAGNOSTICS"
        )
        logger.info(
            "--------------------------------------------------"
        )

        logger.info(
            f"Leverage             : "
            f"{self.leverage:.4f}"
        )

        logger.info(
            f"Expense ratio        : "
            f"{self.expense_ratio:.8f}"
        )

        logger.info(
            f"Treasury first       : "
            f"{treasury.iloc[0] * 100:.8f}%"
        )

        logger.info(
            f"Treasury last        : "
            f"{treasury.iloc[-1] * 100:.8f}%"
        )

        logger.info(
            f"Treasury minimum     : "
            f"{treasury.min() * 100:.8f}%"
        )

        logger.info(
            f"Treasury maximum     : "
            f"{treasury.max() * 100:.8f}%"
        )

        logger.info(
            f"Daily financing first: "
            f"{daily_financing.iloc[0] * 100:.10f}%"
        )

        logger.info(
            f"Daily financing mean : "
            f"{daily_financing.mean() * 100:.10f}%"
        )

        logger.info(
            f"Daily financing max  : "
            f"{daily_financing.max() * 100:.10f}%"
        )

        logger.info(
            f"Daily expense drag   : "
            f"{daily_expense * 100:.10f}%"
        )

        # ==============================================================
        # 7. FULL THEORETICAL LEVERAGED MODEL
        # ==============================================================

        financing_aligned = (
            daily_financing
            .reindex(
                close_return.index
            )
            .ffill()
            .bfill()
        )

        full_model_return = (
            self.leverage
            * close_return
            - financing_aligned
            - daily_expense
        )

        full_model_return = (
            full_model_return
            .clip(
                lower=-0.999999
            )
        )

        full_model_nav = (
            (
                1.0
                + full_model_return
            )
            .cumprod()
        )

        logger.info("")
        logger.info(
            "FULL THEORETICAL LEVERAGED MODEL"
        )
        logger.info(
            "--------------------------------------------------"
        )

        logger.info(
            f"First NAV : "
            f"{full_model_nav.iloc[0]:.12g}"
        )

        logger.info(
            f"Last NAV  : "
            f"{full_model_nav.iloc[-1]:.12g}"
        )

        logger.info(
            f"Minimum NAV : "
            f"{full_model_nav.min():.12g}"
        )

        # ==============================================================
        # 8. HISTORICAL CHECKPOINTS
        # ==============================================================

        logger.info("")
        logger.info(
            "HISTORICAL NAV CHECKPOINTS"
        )
        logger.info(
            "--------------------------------------------------"
        )

        checkpoints = [
            "1999-03-11",
            "2000-03-10",
            "2001-01-02",
            "2002-01-02",
            "2003-01-02",
            "2004-01-02",
            "2005-01-03",
            "2006-01-03",
            "2006-06-20",
        ]

        for checkpoint in checkpoints:

            checkpoint_date = (
                pd.Timestamp(checkpoint)
            )

            valid_close = (
                theoretical_2x_close_nav.index[
                    theoretical_2x_close_nav.index
                    <= checkpoint_date
                ]
            )

            if len(valid_close) == 0:
                continue

            date = valid_close[-1]

            close_nav = float(
                theoretical_2x_close_nav.loc[
                    date
                ]
            )

            full_valid = (
                full_model_nav.index[
                    full_model_nav.index
                    <= date
                ]
            )

            if len(full_valid) > 0:

                full_nav = float(
                    full_model_nav.loc[
                        full_valid[-1]
                    ]
                )

            else:

                full_nav = float("nan")

            logger.info(
                f"{date.date()} | "
                f"2x Close NAV="
                f"{close_nav:.12g} | "
                f"Full NAV="
                f"{full_nav:.12g}"
            )

        logger.info("")
        logger.info(
            "=================================================="
        )
        logger.info(
            "END LEVERAGED SYNTHETIC DIAGNOSTICS"
        )
        logger.info(
            "=================================================="
        )

    # ==================================================================
    # Production NAV builder
    # ==================================================================

    def build_nav(
        self,
        underlying_close: pd.Series,
        treasury_rate: pd.Series,
    ):
        """
        Build the production economic NAV.

        Daily leveraged return:

            leverage × underlying return
            - financing cost
            - expense ratio
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

        leveraged_return = (
            leveraged_return
            .clip(
                lower=-0.999999
            )
        )

        nav = (
            (
                1.0
                + leveraged_return
            )
            .cumprod()
        )

        return (
            nav,
            leveraged_return,
        )

    # ==================================================================
    # Split-aware quoted price
    # ==================================================================

    @staticmethod
    def build_split_aware_price(
        nav: pd.Series,
        historical_splits: pd.Series,
        target_price: float,
    ):
        """
        Convert economic NAV into a quoted synthetic share price.

        Splits modify:

            share count
            quoted price

        Splits do NOT modify NAV.
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
                f"Invalid first NAV: "
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
                    f"Invalid NAV on "
                    f"{date}: {nav_value}"
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

                cumulative_split *= (
                    split_factor
                )

            price = (
                nav_value
                / shares
            )

            if (
                not math.isfinite(price)
                or price <= 0
            ):
                raise ValueError(
                    f"Invalid synthetic price "
                    f"on {date}: {price}"
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