"""
Market signal engine.
"""

from dataclasses import dataclass

from marketpilot.indicators import (
    realized_volatility,
    volatility_ratio,
    simple_moving_average,
    credit_stress,
    donchian_low,
)


@dataclass
class SignalEngine:

    market: dict

    def __post_init__(self):

        qqq = self.market["QQQ"]
        spy = self.market["SPY"]
        hyg = self.market["HYG"]
        lqd = self.market["LQD"]

        # ----------------------------
        # Raw indicator values
        # ----------------------------

        self.rvol = realized_volatility(
            qqq.close,
        ).iloc[-1]

        self.vr = volatility_ratio(
            qqq.close,
        ).iloc[-1]

        sma200 = simple_moving_average(
            spy.close,
            200,
        ).iloc[-1]

        self.spy_distance = (
            (spy.latest_close - sma200)
            / sma200
        ) * 100

        self.credit = credit_stress(
            hyg.close,
            lqd.close,
        ).iloc[-1]

        self.credit_crisis = (
            self.credit < -4.0
        )

        self.donchian_break = (
            donchian_low(
                qqq.close,
                40,
            ).iloc[-1]
        )

        self.donchian_confirmed = (
            self.donchian_break
            and self.rvol >= 0.20
        )

        # ----------------------------
        # Boolean Signals
        # ----------------------------

        #
        # TQQQ -> QLD
        #

        self.rvol_over_qld = self.rvol > 0.18

        self.vr_over_qld = self.vr > 1.25

        self.spy_breakdown = (
            self.spy_distance < -3
        )

        #
        # QLD -> Defensive
        #

        self.rvol_over_defensive = (
            self.rvol > 0.36
        )

        self.vr_over_defensive = (
            self.vr > 1.40
        )

        #
        # Recovery
        #

        self.rvol_clear = (
            self.rvol < 0.14
        )

        self.vr_clear = (
            self.vr < 0.90
        )

        self.spy_clear = (
            self.spy_distance > 3
        )

        #
        # Defensive recovery
        #

        self.rvol_defensive_clear = (
            self.rvol < 0.25
        )

        self.vr_defensive_clear = (
            self.vr < 1.10
        )

        self.spy_recovery = (
            self.spy_distance > -1.5
        )