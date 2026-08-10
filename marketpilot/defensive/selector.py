"""
Defensive asset selection.

Chooses the strongest qualifying defensive asset using
IndicatorEngine calculations.

Qualification rules

    • Positive 30-day momentum
    • Positive 90-day momentum
    • Not excessively extended above its 50 SMA

If nothing qualifies, cash is selected.
"""

from dataclasses import dataclass


@dataclass
class DefensiveChoice:

    symbol: str

    momentum30: float

    momentum90: float

    qualified: bool


class DefensiveSelector:

    def select(

        self,

        indicators,

        profile,

    ):

        candidates = []

        for symbol in profile.defensive_assets:

            m30 = indicators.momentum_30(symbol)

            m90 = indicators.momentum_90(symbol)

            #
            # Not enough history yet.
            #

            if (

                m30 is None

                or

                m90 is None

            ):

                continue

            distance = indicators.distance_from_sma(

                symbol,

                50,

            )

            qualified = (

                m30 > 0

                and

                m90 > 0

                and

                distance < profile.defensive_max_extension

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

            candidate

            for candidate in candidates

            if candidate.qualified

        ]

        if not qualified:

            return DefensiveChoice(

                symbol=profile.cash_asset,

                momentum30=0,

                momentum90=0,

                qualified=True,

            )

        return max(

            qualified,

            key=lambda candidate: candidate.momentum90,

        )