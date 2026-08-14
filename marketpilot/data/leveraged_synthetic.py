"""
Generic synthetic leveraged ETF construction.
"""

from __future__ import annotations

import math

import pandas as pd


class LeveragedSyntheticBuilder:

    def __init__(
        self,
        leverage: float,
        expense_ratio: float,
    ):
        self.leverage = leverage
        self.expense_ratio = expense_ratio

    def build_nav(
        self,
        underlying_close: pd.Series,
        treasury_rate: pd.Series,
    ):

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
            self.expense_ratio / 252.0
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
            leveraged_return.clip(
                lower=-0.999999
            )
        )

        nav = (
            (1.0 + leveraged_return)
            .cumprod()
        )

        return (
            nav,
            leveraged_return,
        )

    @staticmethod
    def build_split_aware_price(
        nav: pd.Series,
        historical_splits: pd.Series,
        target_price: float,
    ):

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

        shares = (
            first_nav / target_price
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
                not math.isfinite(split_factor)
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
                nav_value / shares
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
            applied_splits.append(split_factor)
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