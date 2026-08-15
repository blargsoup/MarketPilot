"""
Synthetic leveraged ETF calculations.

This module is responsible for:

    1. Calculating daily leveraged returns.
    2. Building theoretical economic NAV.
    3. Applying financing costs.
    4. Applying ETF expense drag.
    5. Building a quoted share-price layer from NAV.
    6. Providing diagnostics for leveraged ETF reconstruction.

IMPORTANT:

Economic NAV is independent of stock splits.

Splits belong to leveraged_splits.py.

Historical reference-price construction belongs to
leveraged_reference.py.

Validation belongs to leveraged_validation.py.

This module contains only the mathematical leveraged-return engine.
"""

from __future__ import annotations

import logging
import math

import pandas as pd


logger = logging.getLogger(__name__)


class LeveragedSyntheticBuilder:
    """
    Build synthetic leveraged ETF economic NAV.

    Model:

        leveraged return
            = leverage × underlying return
            - financing cost
            - expense drag

    Financing applies only to the borrowed portion:

        financing exposure = leverage - 1

    Therefore:

        2× ETF -> 1× financing exposure
        3× ETF -> 2× financing exposure
    """

    # ==================================================================
    # Initialization
    # ==================================================================

    def __init__(
        self,
        leverage: float,
        expense_ratio: float,
    ):
        """
        Initialize the synthetic leveraged ETF engine.

        Parameters
        ----------
        leverage:
            Target leverage, e.g. 2.0 or 3.0.

        expense_ratio:
            Annual ETF expense ratio as decimal.

            Example:

                0.0095 = 0.95%
        """

        if (
            not math.isfinite(leverage)
            or leverage <= 0
        ):
            raise ValueError(
                f"Invalid leverage: {leverage}"
            )

        if (
            not math.isfinite(expense_ratio)
            or expense_ratio < 0
        ):
            raise ValueError(
                f"Invalid expense ratio: "
                f"{expense_ratio}"
            )

        self.leverage = float(leverage)
        self.expense_ratio = float(expense_ratio)

    # ==================================================================
    # Treasury normalization
    # ==================================================================

    @staticmethod
    def _normalize_treasury_rate(
        treasury_rate: pd.Series,
    ) -> pd.Series:
        """
        Normalize Treasury data into decimal annual rates.

        The provider currently passes Treasury data after this
        conversion:

            treasury_rate = raw_value / 100.0

        Therefore this method normally receives decimal rates.

        Example:

            raw FRED value:
                5.25

            provider conversion:
                5.25 / 100
                = 0.0525

            normalized:
                0.0525

        The diagnostics previously showed values such as:

            1201.117%

        which strongly indicates a unit mismatch somewhere upstream.

        To prevent the synthetic model from silently applying absurd
        financing costs, this method accepts the following reasonable
        decimal/percentage representations:

            0.0525       -> 5.25%
            5.25         -> 5.25%
            0.1201117    -> 12.01117%
            12.01117     -> 12.01117%

        Values above 100% after normalization are rejected.
        """

        if treasury_rate is None:
            raise ValueError(
                "Treasury rate series is None."
            )

        rate = pd.to_numeric(
            treasury_rate,
            errors="coerce",
        )

        if rate.empty:
            raise ValueError(
                "Treasury rate series is empty."
            )

        if rate.isna().all():
            raise ValueError(
                "Treasury rate series contains "
                "no valid values."
            )

        rate = (
            rate
            .ffill()
            .bfill()
        )

        if rate.isna().any():
            raise ValueError(
                "Treasury rate series contains "
                "NaN values after filling."
            )

        maximum = float(
            rate.abs().max()
        )

        if (
            not math.isfinite(maximum)
        ):
            raise ValueError(
                "Treasury rate contains "
                "non-finite values."
            )

        # --------------------------------------------------------------
        # Interpret the representation.
        #
        # The provider normally passes decimal rates:
        #
        #     0.0525 -> 5.25%
        #
        # If the incoming value is larger than 1 but still reasonable,
        # interpret it as a percentage:
        #
        #     5.25 -> 0.0525
        #
        # --------------------------------------------------------------

        if maximum <= 1.0:

            normalized = rate

        elif maximum <= 100.0:

            normalized = (
                rate / 100.0
            )

        else:

            raise ValueError(
                "Treasury rate appears to contain "
                "an invalid unit or magnitude. "
                f"Maximum received value = "
                f"{maximum:.6f}. "
                "Expected decimal rates "
                "(e.g. 0.0525) or percentage "
                "rates (e.g. 5.25)."
            )

        normalized_maximum = float(
            normalized.abs().max()
        )

        if (
            not math.isfinite(
                normalized_maximum
            )
            or normalized_maximum > 1.0
        ):
            raise ValueError(
                "Normalized Treasury rate is invalid. "
                f"Maximum absolute annual rate = "
                f"{normalized_maximum:.6f}."
            )

        return normalized

    # ==================================================================
    # Daily leveraged return engine
    # ==================================================================

    def _calculate_leveraged_returns(
        self,
        underlying_close: pd.Series,
        treasury_rate: pd.Series,
    ):
        """
        Calculate daily leveraged returns.

        Returns:

            underlying_return
            financing_rate
            daily_financing
            daily_expense
            leveraged_return
        """

        underlying_close = pd.to_numeric(
            underlying_close,
            errors="coerce",
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
                "Insufficient underlying history "
                "to calculate leveraged returns."
            )

        # --------------------------------------------------------------
        # Daily underlying return.
        #
        # return[t] =
        #
        #     Close[t] / Close[t-1] - 1
        #
        # --------------------------------------------------------------

        underlying_return = (
            underlying_close
            .pct_change()
            .dropna()
        )

        if underlying_return.empty:
            raise ValueError(
                "Unable to calculate underlying returns."
            )

        # --------------------------------------------------------------
        # Treasury normalization.
        # --------------------------------------------------------------

        treasury_decimal = (
            self._normalize_treasury_rate(
                treasury_rate
            )
        )

        # --------------------------------------------------------------
        # TREASURY RATE DEBUG DIAGNOSTICS
        # --------------------------------------------------------------
        logger.info("")
        logger.info("Treasury Rate Debug Diagnostics:")
        logger.info("-" * 60)

        raw_treasury = pd.to_numeric(
            treasury_rate,
            errors="coerce",
        )

        logger.info(
            f"Raw Treasury rows        : {len(raw_treasury)}"
        )

        logger.info(
            f"Raw Treasury first date  : "
            f"{raw_treasury.index.min()}"
        )

        logger.info(
            f"Raw Treasury last date   : "
            f"{raw_treasury.index.max()}"
        )

        logger.info(
            f"Raw Treasury first value : "
            f"{raw_treasury.iloc[0]:.8f}"
        )

        logger.info(
            f"Raw Treasury last value  : "
            f"{raw_treasury.iloc[-1]:.8f}"
        )

        logger.info(
            f"Raw Treasury min         : "
            f"{raw_treasury.min():.8f}"
        )

        logger.info(
            f"Raw Treasury max         : "
            f"{raw_treasury.max():.8f}"
        )

        logger.info("")
        logger.info("Normalized Treasury:")
        logger.info(
            f"Normalized first         : "
            f"{treasury_decimal.iloc[0] * 100:.8f}%"
        )

        logger.info(
            f"Normalized last          : "
            f"{treasury_decimal.iloc[-1] * 100:.8f}%"
        )

        logger.info(
            f"Normalized min           : "
            f"{treasury_decimal.min() * 100:.8f}%"
        )

        logger.info(
            f"Normalized max           : "
            f"{treasury_decimal.max() * 100:.8f}%"
        )

        logger.info("")
        logger.info("Treasury Sample Values:")
        logger.info("-" * 60)

        sample_dates = [
            raw_treasury.index.min(),
            pd.Timestamp("2000-01-03"),
            pd.Timestamp("2001-01-02"),
            pd.Timestamp("2002-01-02"),
            pd.Timestamp("2003-01-02"),
            pd.Timestamp("2004-01-02"),
            pd.Timestamp("2005-01-03"),
            pd.Timestamp("2006-01-03"),
            raw_treasury.index.max(),
        ]

        for date in sample_dates:

            if date in raw_treasury.index:

                raw_value = raw_treasury.loc[date]
                normalized_value = (
                    treasury_decimal.loc[date]
                    if date in treasury_decimal.index
                    else float("nan")
                )

                logger.info(
                    f"{date.date()} | "
                    f"Raw={raw_value:.8f} | "
                    f"Normalized={normalized_value * 100:.8f}%"
                )

        logger.info("-" * 60)

        # --------------------------------------------------------------
        # Align Treasury to underlying trading dates.
        # --------------------------------------------------------------

        financing_rate = (
            treasury_decimal
            .reindex(
                underlying_return.index
            )
            .ffill()
            .bfill()
        )

        logger.info("")
        logger.info("Treasury Financing Alignment:")
        logger.info("-" * 60)

        logger.info(
            f"Underlying first date : "
            f"{underlying_return.index.min()}"
        )

        logger.info(
            f"Underlying last date  : "
            f"{underlying_return.index.max()}"
        )

        logger.info(
            f"Financing first date  : "
            f"{financing_rate.index.min()}"
        )

        logger.info(
            f"Financing last date   : "
            f"{financing_rate.index.max()}"
        )

        logger.info(
            f"Financing first rate  : "
            f"{financing_rate.iloc[0] * 100:.8f}%"
        )

        logger.info(
            f"Financing last rate   : "
            f"{financing_rate.iloc[-1] * 100:.8f}%"
        )

        logger.info("")
        logger.info("Financing Rate Checkpoints:")
        logger.info("-" * 60)

        for date in sample_dates:

            if date in financing_rate.index:

                logger.info(
                    f"{date.date()} | "
                    f"Financing={financing_rate.loc[date] * 100:.8f}%"
                )

        logger.info("-" * 60)

        if financing_rate.isna().any():
            raise ValueError(
                "Treasury financing rate contains "
                "NaN values after alignment."
            )

        # --------------------------------------------------------------
        # Annual expense -> daily expense.
        # --------------------------------------------------------------

        daily_expense = (
            self.expense_ratio
            / 252.0
        )

        # --------------------------------------------------------------
        # Borrowed exposure.
        # --------------------------------------------------------------

        financing_exposure = (
            self.leverage - 1.0
        )

        # --------------------------------------------------------------
        # Daily financing cost.
        # --------------------------------------------------------------

        daily_financing = (
            financing_exposure
            * financing_rate
            / 252.0
        )

        # --------------------------------------------------------------
        # Leveraged daily return.
        # --------------------------------------------------------------

        leveraged_return = (
            self.leverage
            * underlying_return
            - daily_financing
            - daily_expense
        )

        # --------------------------------------------------------------
        # Mathematical protection.
        # --------------------------------------------------------------

        leveraged_return = (
            leveraged_return
            .clip(
                lower=-0.999999
            )
        )

        return (
            underlying_return,
            financing_rate,
            daily_financing,
            daily_expense,
            leveraged_return,
        )

    # ==================================================================
    # Build NAV
    # ==================================================================

    def build_nav(
        self,
        underlying_close: pd.Series,
        treasury_rate: pd.Series,
    ):
        """
        Build theoretical leveraged economic NAV.

        This is the primary interface used by LeveragedETFProvider.

        Returns:

            nav
            leveraged_return
        """

        (
            underlying_return,
            financing_rate,
            daily_financing,
            daily_expense,
            leveraged_return,
        ) = self._calculate_leveraged_returns(
            underlying_close=underlying_close,
            treasury_rate=treasury_rate,
        )

        # --------------------------------------------------------------
        # Compound NAV.
        # --------------------------------------------------------------

        nav = (
            (1.0 + leveraged_return)
            .cumprod()
        )

        if nav.empty:
            raise ValueError(
                "Synthetic NAV is empty."
            )

        if nav.isna().any():
            raise ValueError(
                "Synthetic NAV contains NaN values."
            )

        if not nav.apply(
            math.isfinite
        ).all():
            raise ValueError(
                "Synthetic NAV contains "
                "non-finite values."
            )

        if (nav <= 0).any():

            bad_date = nav.index[
                nav <= 0
            ][0]

            raise ValueError(
                "Synthetic NAV became "
                f"non-positive on {bad_date}."
            )

        # --------------------------------------------------------------
        # Production diagnostics.
        # --------------------------------------------------------------

        logger.info(
            "Synthetic return model: "
            f"{self.leverage:.1f}x underlying"
        )

        logger.info(
            "Forward return diagnostics:"
        )

        logger.info(
            f"    First return : "
            f"{leveraged_return.iloc[0] * 100:.6f}%"
        )

        logger.info(
            f"    Worst return : "
            f"{leveraged_return.min() * 100:.6f}%"
        )

        logger.info(
            f"    Best return  : "
            f"{leveraged_return.max() * 100:.6f}%"
        )

        logger.info(
            f"    Mean return  : "
            f"{leveraged_return.mean() * 100:.6f}%"
        )

        logger.info(
            "Treasury financing diagnostics:"
        )

        logger.info(
            f"    Annual rate first : "
            f"{financing_rate.iloc[0] * 100:.6f}%"
        )

        logger.info(
            f"    Annual rate last  : "
            f"{financing_rate.iloc[-1] * 100:.6f}%"
        )

        logger.info(
            f"    Annual rate min   : "
            f"{financing_rate.min() * 100:.6f}%"
        )

        logger.info(
            f"    Annual rate max   : "
            f"{financing_rate.max() * 100:.6f}%"
        )

        logger.info(
            f"    Daily financing first : "
            f"{daily_financing.iloc[0] * 100:.8f}%"
        )

        logger.info(
            f"    Daily financing mean  : "
            f"{daily_financing.mean() * 100:.8f}%"
        )

        logger.info(
            f"    Daily financing max   : "
            f"{daily_financing.max() * 100:.8f}%"
        )

        logger.info(
            f"    Daily expense drag    : "
            f"{daily_expense * 100:.8f}%"
        )

        return (
            nav,
            leveraged_return,
        )

    # ==================================================================
    # Compatibility alias
    # ==================================================================

    def build_generic_synthetic_nav(
        self,
        underlying_close: pd.Series,
        treasury_rate: pd.Series,
    ):
        """
        Compatibility wrapper for older callers.
        """

        return self.build_nav(
            underlying_close=underlying_close,
            treasury_rate=treasury_rate,
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
        Convert economic NAV into quoted share price.

        NAV is never modified by splits.

        A forward split:

            shares *= split
            price  /= split

        A reverse split:

            shares *= split
            price  /= split

        Therefore:

            shares × price == NAV

        throughout the series.
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

        nav = pd.to_numeric(
            nav,
            errors="coerce",
        )

        if nav.isna().any():
            raise ValueError(
                "NAV contains NaN values."
            )

        if (
            ~nav.apply(math.isfinite)
        ).any():
            raise ValueError(
                "NAV contains non-finite values."
            )

        if (nav <= 0).any():

            bad_date = nav.index[
                nav <= 0
            ][0]

            raise ValueError(
                f"NAV is non-positive on {bad_date}."
            )

        if (
            not math.isfinite(
                target_price
            )
            or target_price <= 0
        ):
            raise ValueError(
                f"Invalid target price: "
                f"{target_price}"
            )

        historical_splits = (
            historical_splits
            .reindex(nav.index)
            .fillna(1.0)
        )

        historical_splits = (
            pd.to_numeric(
                historical_splits,
                errors="coerce",
            )
            .fillna(1.0)
        )

        first_nav = float(
            nav.iloc[0]
        )

        # --------------------------------------------------------------
        # Initial synthetic share count.
        # --------------------------------------------------------------

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

            # ----------------------------------------------------------
            # Apply actual historical split event.
            #
            # This changes share count only.
            # ----------------------------------------------------------

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

    # ==================================================================
    # Diagnostics
    # ==================================================================

    def diagnose(
        self,
        underlying_close: pd.Series,
        underlying_adj_close: pd.Series | None,
        treasury_rate: pd.Series,
        symbol: str,
    ) -> None:
        """
        Run detailed diagnostics for a synthetic leveraged ETF.

        The diagnostics intentionally use the underlying Close series
        for the production model.

        Adj Close is displayed for comparison only.
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

        close = pd.to_numeric(
            underlying_close,
            errors="coerce",
        ).dropna()

        close = close[
            close > 0
        ]

        if len(close) < 2:
            raise ValueError(
                "Insufficient Close data for diagnostics."
            )

        # --------------------------------------------------------------
        # QQQ price data.
        # --------------------------------------------------------------

        logger.info("")
        logger.info("QQQ PRICE DATA")
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

        # --------------------------------------------------------------
        # Adj Close comparison.
        # --------------------------------------------------------------

        if underlying_adj_close is not None:

            adj = pd.to_numeric(
                underlying_adj_close,
                errors="coerce",
            ).reindex(
                close.index
            )

            adj = adj[
                adj > 0
            ]

            if not adj.empty:

                logger.info("")
                logger.info(
                    "QQQ ADJUSTED PRICE DATA"
                )

                logger.info(
                    "--------------------------------------------------"
                )

                logger.info(
                    f"First Adj Close  : "
                    f"{adj.iloc[0]:.10f}"
                )

                logger.info(
                    f"Last Adj Close   : "
                    f"{adj.iloc[-1]:.10f}"
                )

                logger.info(
                    f"Minimum Adj Close: "
                    f"{adj.min():.10f}"
                )

                logger.info(
                    f"Maximum Adj Close: "
                    f"{adj.max():.10f}"
                )

                common = pd.concat(
                    [
                        close.rename("Close"),
                        adj.rename("Adj Close"),
                    ],
                    axis=1,
                ).dropna()

                if not common.empty:

                    difference = (
                        common["Adj Close"]
                        / common["Close"]
                        - 1.0
                    )

                    logger.info(
                        f"Adj/Close first : "
                        f"{difference.iloc[0] * 100:.6f}%"
                    )

                    logger.info(
                        f"Adj/Close last  : "
                        f"{difference.iloc[-1] * 100:.6f}%"
                    )

                    logger.info(
                        f"Adj/Close min   : "
                        f"{difference.min() * 100:.6f}%"
                    )

                    logger.info(
                        f"Adj/Close max   : "
                        f"{difference.max() * 100:.6f}%"
                    )

        # --------------------------------------------------------------
        # Daily returns.
        # --------------------------------------------------------------

        daily_return = (
            close
            .pct_change()
            .dropna()
        )

        logger.info("")
        logger.info(
            "DAILY RETURN DIAGNOSTICS"
        )

        logger.info(
            "--------------------------------------------------"
        )

        logger.info(
            f"Close first return : "
            f"{daily_return.iloc[0] * 100:.8f}%"
        )

        logger.info(
            f"Close worst return : "
            f"{daily_return.min() * 100:.8f}%"
        )

        logger.info(
            f"Close best return  : "
            f"{daily_return.max() * 100:.8f}%"
        )

        logger.info(
            f"Close mean return  : "
            f"{daily_return.mean() * 100:.8f}%"
        )

        # --------------------------------------------------------------
        # Theoretical pure 2x Close-return NAV.
        #
        # This intentionally excludes:
        #
        #     financing
        #     expenses
        #
        # It tells us what a perfect daily-reset 2x ETF would have
        # produced from the QQQ Close returns alone.
        # --------------------------------------------------------------

        pure_2x_return = (
            2.0
            * daily_return
        )

        pure_2x_return = (
            pure_2x_return
            .clip(
                lower=-0.999999
            )
        )

        pure_2x_nav = (
            (1.0 + pure_2x_return)
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
            f"{pure_2x_nav.iloc[0]:.12g}"
        )

        logger.info(
            f"Last NAV  : "
            f"{pure_2x_nav.iloc[-1]:.12g}"
        )

        logger.info(
            f"Minimum NAV : "
            f"{pure_2x_nav.min():.12g}"
        )

        # --------------------------------------------------------------
        # Treasury diagnostics.
        # --------------------------------------------------------------

        normalized_treasury = (
            self._normalize_treasury_rate(
                treasury_rate
            )
        )

        financing_rate = (
            normalized_treasury
            .reindex(
                daily_return.index
            )
            .ffill()
            .bfill()
        )

        financing_exposure = (
            self.leverage - 1.0
        )

        daily_financing = (
            financing_exposure
            * financing_rate
            / 252.0
        )

        daily_expense = (
            self.expense_ratio
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
            f"{financing_rate.iloc[0] * 100:.8f}%"
        )

        logger.info(
            f"Treasury last        : "
            f"{financing_rate.iloc[-1] * 100:.8f}%"
        )

        logger.info(
            f"Treasury minimum     : "
            f"{financing_rate.min() * 100:.8f}%"
        )

        logger.info(
            f"Treasury maximum     : "
            f"{financing_rate.max() * 100:.8f}%"
        )

        logger.info(
            f"Daily financing first: "
            f"{daily_financing.iloc[0] * 100:.8f}%"
        )

        logger.info(
            f"Daily financing mean : "
            f"{daily_financing.mean() * 100:.8f}%"
        )

        logger.info(
            f"Daily financing max  : "
            f"{daily_financing.max() * 100:.8f}%"
        )

        logger.info(
            f"Daily expense drag   : "
            f"{daily_expense * 100:.8f}%"
        )

        # --------------------------------------------------------------
        # Full theoretical model.
        # --------------------------------------------------------------

        full_return = (
            self.leverage
            * daily_return
            - daily_financing
            - daily_expense
        )

        full_return = (
            full_return
            .clip(
                lower=-0.999999
            )
        )

        full_nav = (
            (1.0 + full_return)
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
            f"{full_nav.iloc[0]:.12g}"
        )

        logger.info(
            f"Last NAV  : "
            f"{full_nav.iloc[-1]:.12g}"
        )

        logger.info(
            f"Minimum NAV : "
            f"{full_nav.min():.12g}"
        )

        # --------------------------------------------------------------
        # Historical checkpoints.
        # --------------------------------------------------------------

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

            date = pd.Timestamp(
                checkpoint
            )

            if date not in pure_2x_nav.index:
                continue

            logger.info(
                f"{checkpoint} | "
                f"2x Close NAV="
                f"{pure_2x_nav.loc[date]:.12g} | "
                f"Full NAV="
                f"{full_nav.loc[date]:.12g}"
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

    ############################
    def diagnose_against_actual(
        self,
        underlying_close: pd.Series,
        treasury_rate: pd.Series,
        actual_history: pd.DataFrame,
        symbol: str = "QLD",
    ) -> pd.DataFrame:
        """
        Compare the theoretical synthetic leveraged ETF against
        the actual ETF over the period where the actual ETF exists.

        The comparison is normalized to 1.0 on the actual ETF's
        first trading day.

        Columns returned:

            Actual Close
            Actual Adj Close
            Synthetic NAV
            Pure 2x NAV
            Actual Daily Return
            Synthetic Daily Return
            Pure 2x Daily Return
            Synthetic Tracking Error
            Cumulative Tracking Difference
        """

        logger.info("")
        logger.info("=" * 70)
        logger.info(
            f"ACTUAL vs SYNTHETIC DIAGNOSTIC: {symbol}"
        )
        logger.info("=" * 70)

        # --------------------------------------------------------------
        # Normalize indexes
        # --------------------------------------------------------------

        underlying_close = underlying_close.copy()
        treasury_rate = treasury_rate.copy()
        actual = actual_history.copy()

        underlying_close.index = pd.to_datetime(
            underlying_close.index
        )

        treasury_rate.index = pd.to_datetime(
            treasury_rate.index
        )

        actual.index = pd.to_datetime(
            actual.index
        )

        underlying_close = (
            underlying_close
            .sort_index()
            .dropna()
        )

        treasury_rate = (
            treasury_rate
            .sort_index()
        )

        actual = (
            actual
            .sort_index()
        )

        # --------------------------------------------------------------
        # Normalize actual price columns
        # --------------------------------------------------------------

        if "Close" not in actual.columns:
            raise ValueError(
                f"{symbol}: actual history has no Close column."
            )

        if "Adj Close" not in actual.columns:
            actual["Adj Close"] = actual["Close"]

        actual["Close"] = pd.to_numeric(
            actual["Close"],
            errors="coerce",
        )

        actual["Adj Close"] = pd.to_numeric(
            actual["Adj Close"],
            errors="coerce",
        )

        actual = actual.dropna(
            subset=["Close", "Adj Close"]
        )

        # --------------------------------------------------------------
        # Actual ETF inception
        # --------------------------------------------------------------

        actual_start = actual.index.min()

        logger.info(
            f"Actual inception : {actual_start.date()}"
        )

        logger.info(
            f"Actual last date  : "
            f"{actual.index.max().date()}"
        )

        # --------------------------------------------------------------
        # Build the full theoretical NAV.
        #
        # IMPORTANT:
        #
        # We use the FULL underlying history here, not merely the
        # pre-inception portion used by the production builder.
        #
        # This allows us to compare the theoretical model directly
        # against actual QLD after June 21, 2006.
        # --------------------------------------------------------------

        synthetic_nav, synthetic_return = (
            self.build_nav(
                underlying_close=underlying_close,
                treasury_rate=treasury_rate,
            )
        )

        # --------------------------------------------------------------
        # Pure 2x theoretical return.
        #
        # This is useful because it separates:
        #
        #     leverage/path dependency
        #
        # from:
        #
        #     financing + expense drag
        # --------------------------------------------------------------

        underlying_return = (
            underlying_close
            .pct_change()
        )

        pure_2x_return = (
            self.leverage
            * underlying_return
        )

        pure_2x_return = (
            pure_2x_return
            .clip(lower=-0.999999)
        )

        pure_2x_nav = (
            1.0 + pure_2x_return
        ).cumprod()

        # --------------------------------------------------------------
        # Build comparison frame
        # --------------------------------------------------------------

        comparison = pd.DataFrame(
            {
                "Actual Close": actual["Close"],
                "Actual Adj Close": actual["Adj Close"],
                "Synthetic NAV": synthetic_nav,
                "Pure 2x NAV": pure_2x_nav,
            }
        )

        comparison = (
            comparison
            .dropna()
            .loc[actual_start:]
        )

        if comparison.empty:
            raise ValueError(
                f"{symbol}: no overlapping dates between "
                "synthetic and actual history."
            )

        # --------------------------------------------------------------
        # Normalize everything to 1.0 at actual inception.
        # --------------------------------------------------------------

        for column in [
            "Actual Close",
            "Actual Adj Close",
            "Synthetic NAV",
            "Pure 2x NAV",
        ]:

            first_value = float(
                comparison[column].iloc[0]
            )

            if (
                not math.isfinite(first_value)
                or first_value <= 0
            ):
                raise ValueError(
                    f"{symbol}: invalid first value for "
                    f"{column}: {first_value}"
                )

            comparison[column] = (
                comparison[column]
                / first_value
            )

        # --------------------------------------------------------------
        # Daily returns
        # --------------------------------------------------------------

        comparison[
            "Actual Daily Return"
        ] = (
            comparison["Actual Close"]
            .pct_change()
        )

        comparison[
            "Actual Adj Daily Return"
        ] = (
            comparison["Actual Adj Close"]
            .pct_change()
        )

        comparison[
            "Synthetic Daily Return"
        ] = (
            comparison["Synthetic NAV"]
            .pct_change()
        )

        comparison[
            "Pure 2x Daily Return"
        ] = (
            comparison["Pure 2x NAV"]
            .pct_change()
        )

        # --------------------------------------------------------------
        # Tracking error
        # --------------------------------------------------------------

        comparison[
            "Synthetic Tracking Error"
        ] = (
            comparison["Synthetic Daily Return"]
            - comparison["Actual Daily Return"]
        )

        comparison[
            "Pure 2x Tracking Error"
        ] = (
            comparison["Pure 2x Daily Return"]
            - comparison["Actual Daily Return"]
        )

        # --------------------------------------------------------------
        # Cumulative tracking difference
        # --------------------------------------------------------------

        comparison[
            "Synthetic vs Actual"
        ] = (
            comparison["Synthetic NAV"]
            / comparison["Actual Close"]
            - 1.0
        )

        comparison[
            "Pure 2x vs Actual"
        ] = (
            comparison["Pure 2x NAV"]
            / comparison["Actual Close"]
            - 1.0
        )

        # ==============================================================
        # LOG SUMMARY
        # ==============================================================

        logger.info("")
        logger.info(
            "NORMALIZED PERFORMANCE"
        )
        logger.info("-" * 70)

        logger.info(
            f"Actual Close       : "
            f"{comparison['Actual Close'].iloc[-1]:.6f}x"
        )

        logger.info(
            f"Actual Adj Close   : "
            f"{comparison['Actual Adj Close'].iloc[-1]:.6f}x"
        )

        logger.info(
            f"Pure 2x QQQ        : "
            f"{comparison['Pure 2x NAV'].iloc[-1]:.6f}x"
        )

        logger.info(
            f"Full synthetic     : "
            f"{comparison['Synthetic NAV'].iloc[-1]:.6f}x"
        )

        logger.info("")

        logger.info(
            f"Pure 2x vs Actual  : "
            f"{comparison['Pure 2x vs Actual'].iloc[-1] * 100:.4f}%"
        )

        logger.info(
            f"Synthetic vs Actual: "
            f"{comparison['Synthetic vs Actual'].iloc[-1] * 100:.4f}%"
        )

        # ==============================================================
        # DAILY TRACKING STATISTICS
        # ==============================================================

        daily = comparison.dropna(
            subset=[
                "Actual Daily Return",
                "Synthetic Daily Return",
                "Pure 2x Daily Return",
            ]
        )

        if not daily.empty:

            synthetic_error = (
                daily["Synthetic Tracking Error"]
            )

            pure_error = (
                daily["Pure 2x Tracking Error"]
            )

            logger.info("")
            logger.info(
                "DAILY TRACKING STATISTICS"
            )
            logger.info("-" * 70)

            logger.info(
                f"Trading days        : "
                f"{len(daily)}"
            )

            logger.info(
                f"Synthetic correlation: "
                f"{daily['Actual Daily Return'].corr(
                    daily['Synthetic Daily Return']
                ):.6f}"
            )

            logger.info(
                f"Pure 2x correlation : "
                f"{daily['Actual Daily Return'].corr(
                    daily['Pure 2x Daily Return']
                ):.6f}"
            )

            logger.info(
                f"Synthetic mean error: "
                f"{synthetic_error.mean() * 100:.6f}%"
            )

            logger.info(
                f"Synthetic RMSE     : "
                f"{math.sqrt(
                    (synthetic_error ** 2).mean()
                ) * 100:.6f}%"
            )

            logger.info(
                f"Synthetic max error: "
                f"{synthetic_error.abs().max() * 100:.6f}%"
            )

            logger.info(
                f"Pure 2x mean error : "
                f"{pure_error.mean() * 100:.6f}%"
            )

            logger.info(
                f"Pure 2x RMSE       : "
                f"{math.sqrt(
                    (pure_error ** 2).mean()
                ) * 100:.6f}%"
            )

        # ==============================================================
        # CHECKPOINTS
        # ==============================================================

        logger.info("")
        logger.info(
            "HISTORICAL CHECKPOINTS"
        )
        logger.info("-" * 70)

        checkpoints = [
            1,
            5,
            20,
            30,
            60,
            126,
            252,
            504,
            756,
            1000,
            1500,
            2000,
            3000,
            4000,
        ]

        for days in checkpoints:

            if days >= len(comparison):
                continue

            row = comparison.iloc[days]

            logger.info(
                f"{days:4d} days | "
                f"{row.name.date()} | "
                f"Actual={row['Actual Close']:.6f}x | "
                f"Pure2x={row['Pure 2x NAV']:.6f}x | "
                f"Synthetic={row['Synthetic NAV']:.6f}x | "
                f"Syn-Actual="
                f"{row['Synthetic vs Actual'] * 100:+.3f}%"
            )

        # ==============================================================
        # FINAL SUMMARY
        # ==============================================================

        logger.info("")
        logger.info("=" * 70)
        logger.info(
            f"END ACTUAL vs SYNTHETIC DIAGNOSTIC: {symbol}"
        )
        logger.info("=" * 70)
        logger.info("")

        return comparison
    
# ----------------------------------------------------------------------
# Backwards-compatible class alias
# ----------------------------------------------------------------------

LeveragedSyntheticEngine = LeveragedSyntheticBuilder


# ----------------------------------------------------------------------
# Backwards-compatible standalone function
# ----------------------------------------------------------------------

def build_generic_synthetic_nav(
    underlying_close: pd.Series,
    treasury_rate: pd.Series,
    leverage: float,
    expense_ratio: float,
):
    """
    Standalone compatibility function.
    """

    builder = LeveragedSyntheticBuilder(
        leverage=leverage,
        expense_ratio=expense_ratio,
    )

    return builder.build_nav(
        underlying_close=underlying_close,
        treasury_rate=treasury_rate,
    )