"""
Repository-specific leveraged ETF reference models.
"""

from __future__ import annotations

import math

import pandas as pd

from .leveraged_splits import LeveragedSplitManager


class LeveragedReferenceBuilder:

    @classmethod
    def build_tqqq(
        cls,
        actual_start: pd.Timestamp,
        actual_first_close: float,
    ):

        reference = (
            LeveragedSplitManager
            .load_simulated_tqqq()
        )

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

        synthetic_last = float(
            reference_close.iloc[-1]
        )

        if (
            not math.isfinite(synthetic_last)
            or synthetic_last <= 0
        ):
            raise ValueError(
                "Invalid final simulated TQQQ "
                "reference price"
            )

        # Price layer.
        price_scale = (
            actual_first_close
            / synthetic_last
        )

        synthetic_price = (
            reference_close
            * price_scale
        )

        # Economic NAV layer.
        synthetic_nav = (
            reference_close
            / synthetic_last
        )

        # Historical split metadata.
        split_series = (
            reference["split"]
            .astype(float)
        )

        cumulative_split = (
            split_series.cumprod()
        )

        return (
            synthetic_price,
            synthetic_nav,
            split_series,
            cumulative_split,
        )