"""
Synthetic leveraged ETF calculations.

This module is responsible for:

    1. Calculating daily leveraged returns.
    2. Building theoretical economic NAV.
    3. Applying financing costs.
    4. Applying ETF expense drag.
    5. Building a quoted share-price layer from NAV.

IMPORTANT:

Economic NAV is independent of stock splits.

Splits belong to leveraged_splits.py.

Historical reference-price construction belongs to
leveraged_reference.py.

Validation belongs to leveraged_validation.py.

This module should contain the mathematical leveraged-return engine.
"""

from __future__ import annotations

import logging
import math

import pandas as pd


logger = logging.getLogger(__name__)


class LeveragedSyntheticBuilder:
    """
    Build synthetic leveraged ETF economic NAV.

    The model is:

        leveraged return
            = leverage × underlying return
            - financing cost
            - expense drag

    Financing applies only to the borrowed portion:

        financing exposure = leverage - 1

    For example:

        2× ETF:
            financing exposure = 1×

        3× ETF:
            financing exposure = 2×
    """

    # ------------------------------------------------------------------
    # Treasury normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_treasury_rate(
        treasury_rate: pd.Series,
    ) -> pd.Series:
        """
        Normalize the Treasury series into decimal annual rates.

        MarketPilot's FRED/TBILL provider is currently returning values
        such as:

            1201.117
            1501.959

        These represent:

            12.01117%
            15.01959%

        Therefore the conversion is:

            raw / 10000

        producing:

            0.1201117
            0.1501959

        which are decimal annual rates.

        The function deliberately checks the resulting magnitude so a
        unit error cannot silently produce a multi-percent-per-day
        financing charge.
        """

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
                "Treasury rate series contains no valid values."
            )

        rate = (
            rate
            .ffill()
            .bfill()
        )

        if rate.isna().any():
            raise ValueError(
                "Treasury rate series contains NaN values "
                "after forward/backward filling."
            )

        # --------------------------------------------------------------
        # Current FRED provider representation.
        #
        # Example:
        #
        #     1201.117 -> 0.1201117
        #
        #     1501.959 -> 0.1501959
        #
        # --------------------------------------------------------------

        normalized = (
            rate
            / 10000.0
        )

        # --------------------------------------------------------------
        # Sanity check.
        #
        # A Treasury rate greater than 100% is almost certainly a unit
        # conversion error.
        # --------------------------------------------------------------

        maximum = float(
            normalized.abs().max()
        )

        if (
            not math.isfinite(maximum)
            or maximum > 1.0
        ):
            raise ValueError(
                "Normalized Treasury rate is invalid. "
                f"Maximum absolute annual rate = "
                f"{maximum:.6f}. "
                "Expected decimal annual rates."
            )

        return normalized

    # ------------------------------------------------------------------
    # Daily leveraged return
    # ------------------------------------------------------------------

    def build_synthetic_nav(
        self,
        underlying_close: pd.Series,
        treasury_rate: pd.Series,
        leverage: float,
        expense_ratio: float,
    ):
        """
        Build theoretical leveraged ETF NAV.

        Parameters
        ----------
        underlying_close:
            Underlying ETF price series.

        treasury_rate:
            Annual Treasury rate series.

        leverage:
            Target leverage, e.g. 2.0 or 3.0.

        expense_ratio:
            Annual ETF expense ratio as decimal.

            Example:

                0.0095 = 0.95%

        Returns
        -------
        nav:
            Synthetic economic NAV.

        leveraged_return:
            Daily leveraged return before compounding.
        """

        if underlying_close is None:
            raise ValueError(
                "Underlying close series is None."
            )

        if treasury_rate is None:
            raise ValueError(
                "Treasury rate series is None."
            )

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

        # --------------------------------------------------------------
        # Normalize underlying.
        # --------------------------------------------------------------

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
        # This intentionally uses the supplied Close series directly.
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
        # Normalize Treasury.
        # --------------------------------------------------------------

        treasury_decimal = (
            self._normalize_treasury_rate(
                treasury_rate
            )
        )

        # --------------------------------------------------------------
        # Align Treasury to trading dates.
        # --------------------------------------------------------------

        financing_rate = (
            treasury_decimal
            .reindex(
                underlying_return.index
            )
            .ffill()
            .bfill()
        )

        if financing_rate.isna().any():
            raise ValueError(
                "Treasury financing rate contains "
                "NaN values after alignment."
            )

        # --------------------------------------------------------------
        # Daily expense drag.
        #
        # Expense ratio is annualized.
        #
        # Example:
        #
        #     0.95% / 252
        #
        # --------------------------------------------------------------

        daily_expense = (
            expense_ratio
            / 252.0
        )

        # --------------------------------------------------------------
        # Financing exposure.
        #
        # A 2× ETF borrows approximately 1×.
        #
        # A 3× ETF borrows approximately 2×.
        #
        # Therefore:
        #
        #     financing exposure = leverage - 1
        #
        # --------------------------------------------------------------

        financing_exposure = (
            leverage - 1.0
        )

        daily_financing = (
            financing_exposure
            * financing_rate
            / 252.0
        )

        # --------------------------------------------------------------
        # Leveraged daily return.
        # --------------------------------------------------------------

        leveraged_return = (
            leverage
            * underlying_return
            - daily_financing
            - daily_expense
        )

        # --------------------------------------------------------------
        # Prevent mathematical collapse below -100%.
        #
        # This is NOT a market assumption.
        #
        # It simply prevents:
        #
        #     1 + return <= 0
        #
        # from making the compounded NAV invalid.
        # --------------------------------------------------------------

        leveraged_return = (
            leveraged_return
            .clip(
                lower=-0.999999
            )
        )

        # --------------------------------------------------------------
        # Compound economic NAV.
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
        # Diagnostics.
        # --------------------------------------------------------------

        logger.info(
            "Synthetic return model: "
            f"{leverage:.1f}x underlying"
        )

        logger.info(
            "Underlying return diagnostics:"
        )

        logger.info(
            f"    First return : "
            f"{underlying_return.iloc[0] * 100:.6f}%"
        )

        logger.info(
            f"    Worst return : "
            f"{underlying_return.min() * 100:.6f}%"
        )

        logger.info(
            f"    Best return  : "
            f"{underlying_return.max() * 100:.6f}%"
        )

        logger.info(
            f"    Mean return  : "
            f"{underlying_return.mean() * 100:.6f}%"
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

        logger.info(
            "Synthetic NAV diagnostics:"
        )

        logger.info(
            f"    First NAV : "
            f"{nav.iloc[0]:.12g}"
        )

        logger.info(
            f"    Last NAV  : "
            f"{nav.iloc[-1]:.12g}"
        )

        logger.info(
            f"    Minimum NAV : "
            f"{nav.min():.12g}"
        )

        return (
            nav,
            leveraged_return,
        )

    # ------------------------------------------------------------------
    # Generic compatibility method
    # ------------------------------------------------------------------

    def build_generic_synthetic_nav(
        self,
        underlying_close: pd.Series,
        treasury_rate: pd.Series,
    ):
        """
        Compatibility wrapper for the existing MarketPilot provider.

        The provider already stores leverage and expense ratio on the
        LeveragedETFProvider instance, so this method allows the engine
        to be used without changing that calling convention.
        """

        if not hasattr(
            self,
            "leverage",
        ):
            raise AttributeError(
                "LeveragedSyntheticEngine requires "
                "'leverage' when using "
                "build_generic_synthetic_nav()."
            )

        if not hasattr(
            self,
            "expense_ratio",
        ):
            raise AttributeError(
                "LeveragedSyntheticEngine requires "
                "'expense_ratio' when using "
                "build_generic_synthetic_nav()."
            )

        return self.build_synthetic_nav(
            underlying_close=underlying_close,
            treasury_rate=treasury_rate,
            leverage=self.leverage,
            expense_ratio=self.expense_ratio,
        )


# ======================================================================
# Backwards-compatible standalone function
# ======================================================================

def build_generic_synthetic_nav(
    underlying_close: pd.Series,
    treasury_rate: pd.Series,
    leverage: float,
    expense_ratio: float,
):
    """
    Standalone compatibility function.

    This allows existing code that imports the mathematical engine
    directly to continue working.
    """

    engine = LeveragedSyntheticEngine()

    return engine.build_synthetic_nav(
        underlying_close=underlying_close,
        treasury_rate=treasury_rate,
        leverage=leverage,
        expense_ratio=expense_ratio,
    )