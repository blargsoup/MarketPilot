"""
Validation and diagnostic helpers for leveraged ETF histories.
"""

from __future__ import annotations

import math

import pandas as pd


class LeveragedHistoryValidator:

    @staticmethod
    def validate(
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
                ~prices[column]
                .apply(math.isfinite)
            ).any():
                raise ValueError(
                    f"{symbol}: infinite "
                    f"{column} values"
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