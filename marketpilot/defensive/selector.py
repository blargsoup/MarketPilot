"""
Defensive asset selection.
"""

from dataclasses import dataclass


@dataclass
class DefensiveChoice:

    symbol: str

    momentum30: float

    momentum90: float

    qualified: bool


class DefensiveSelector:

    SYMBOLS = (
        "TLT",
        "GLD",
        "XLU",
        "XLE",
    )

    def select(self, market):

        candidates = []

        for symbol in self.SYMBOLS:

            history = market[symbol]

            close = history.close

            if len(close) < 100:
                continue

            m30 = (
                close.iloc[-1]
                / close.iloc[-31]
                - 1
            ) * 100

            m90 = (
                close.iloc[-1]
                / close.iloc[-91]
                - 1
            ) * 100

            qualified = (
                m30 > 0
                and m90 > 0
            )

            candidates.append(
                DefensiveChoice(
                    symbol=symbol,
                    momentum30=m30,
                    momentum90=m90,
                    qualified=qualified,
                )
            )

        qualified = [
            c
            for c in candidates
            if c.qualified
        ]

        if not qualified:

            return DefensiveChoice(
                symbol="CASH",
                momentum30=0,
                momentum90=0,
                qualified=True,
            )

        return max(
            qualified,
            key=lambda x: x.momentum90,
        )