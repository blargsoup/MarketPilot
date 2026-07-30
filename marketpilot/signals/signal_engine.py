"""
Converts technical indicators into boolean trading signals.

The IndicatorEngine performs all calculations.

SignalEngine simply applies the strategy thresholds.
"""

from dataclasses import dataclass

from marketpilot.indicators import IndicatorEngine


@dataclass
class SignalEngine:

    market: object

    profile: object

    def __post_init__(self):

        indicators = IndicatorEngine(

            self.market,

            self.profile,

        )

        #
        # Raw indicator values.
        #

        self.rvol = indicators.volatility.rvol_21

        self.vr = indicators.volatility.volume_ratio

        self.spy_distance = (

            indicators.trend.distance_from_200sma

        )

        self.credit = (

            indicators.credit.spread_20

        )

        self.donchian = (

            indicators.breakout.donchian_break

        )

        #
        # Moderate risk thresholds.
        #

        self.rvol_over_qld = (

            self.rvol

            > self.profile.rvol_qld

        )

        self.vr_over_qld = (

            self.vr

            > self.profile.vr_qld

        )

        #
        # Defensive thresholds.
        #

        self.rvol_over_defensive = (

            self.rvol

            > self.profile.rvol_defensive

        )

        self.vr_over_defensive = (

            self.vr

            > self.profile.vr_defensive

        )

        #
        # Recovery.
        #

        self.rvol_clear = (

            self.rvol

            < self.profile.rvol_qld

        )

        self.vr_clear = (

            self.vr

            < self.profile.vr_qld

        )

        self.rvol_defensive_clear = (

            self.rvol

            < self.profile.rvol_defensive

        )

        self.vr_defensive_clear = (

            self.vr

            < self.profile.vr_defensive

        )

        #
        # Trend.
        #

        self.spy_breakdown = (

            self.spy_distance

            < self.profile.spy_breakdown

        )

        self.spy_clear = not self.spy_breakdown

        self.spy_recovery = not self.spy_breakdown

        #
        # Credit.
        #

        self.credit_crisis = (

            self.credit

            < self.profile.credit_threshold

        )

        #
        # Breakouts.
        #

        self.donchian_break = self.donchian

        self.donchian_confirmed = (

            self.donchian

            and self.rvol_over_defensive

        )