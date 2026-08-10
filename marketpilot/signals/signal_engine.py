"""
Market Signal Engine

The SignalEngine converts raw indicator values into boolean
conditions that strategies can evaluate.

IndicatorEngine performs all mathematical calculations.

SignalEngine applies strategy thresholds.

This separation keeps strategies readable while allowing the
indicator calculations to be reused throughout MarketPilot.
"""

from dataclasses import dataclass

from marketpilot.indicators import IndicatorEngine


@dataclass
class SignalEngine:

    market: object

    profile: object

    regime: object

    donchian_regime: object

    def __post_init__(self):

        ###############################################################
        # Calculate indicators
        ###############################################################

        indicators = IndicatorEngine(

            self.market,

            self.profile,

        )

        ###############################################################
        # Raw indicator values
        ###############################################################

        self.relative_volume = indicators.relative_volume

        self.realized_volatility = indicators.realized_volatility

        #
        # Temporary compatibility
        #

        self.rvol = self.realized_volatility

        self.vr = indicators.volatility_ratio

        self.spy_distance = indicators.distance_from_sma(

            self.profile.trend_asset,

            200,

        )

        self.credit = indicators.credit_stress

        self.donchian = indicators.donchian_break

        self.momentum30 = indicators.momentum_30

        self.momentum90 = indicators.momentum_90

        ###############################################################
        # Market Regime
        ###############################################################

        self.market_armed = self.regime.armed

        self.risk_enabled = self.regime.risk_enabled

        ###############################################################
        # Moderate Risk Thresholds
        ###############################################################

        self.rvol_over_qld = (

            self.rvol

            > self.profile.rvol_qld

        )

        self.vr_over_qld = (

            self.vr

            > self.profile.vr_qld

        )

        ###############################################################
        # Defensive Thresholds
        ###############################################################

        self.rvol_over_defensive = (

            self.rvol

            > self.profile.rvol_defensive

        )

        self.vr_over_defensive = (

            self.vr

            > self.profile.vr_defensive

        )

        ###############################################################
        # Recovery Thresholds
        ###############################################################

        #
        # Moderate -> Aggressive
        #
        # All must be true:
        # RVol < 14%
        # VR < 0.90
        # SPY > +3% above 200 SMA
        #

        self.rvol_clear = (
            self.rvol < self.profile.rvol_recovery
        )

        self.vr_clear = (
            self.vr < self.profile.vr_recovery
        )

        #
        # Defensive -> Moderate
        #
        # Normal exit conditions:
        # RVol < 25%
        # VR < 1.10
        # SPY > -1.5% below 200 SMA
        #

        self.rvol_defensive_clear = (
            self.rvol < self.profile.rvol_defensive_recovery
        )

        self.vr_defensive_clear = (
            self.vr < self.profile.vr_defensive_recovery
        )

        ###############################################################
        # Trend
        ###############################################################

        self.spy_breakdown = (
            self.spy_distance < self.profile.spy_breakdown
        )

        self.spy_clear = (
            self.spy_distance > self.profile.spy_clear
        )

        self.spy_recovery = (
            self.spy_distance > self.profile.spy_recovery
        )

        ###############################################################
        # Credit
        ###############################################################

        self.credit_crisis = (
            self.credit < self.profile.credit_threshold
        )

        ###############################################################
        # Donchian
        ###############################################################

        self.donchian_break = self.donchian

        self.donchian_confirmed = (
            self.donchian
            and
            self.rvol >= self.profile.donchian_rvol
        )

        ###############################################################
        # Donchian Recovery
        ###############################################################

        close = indicators.signal_history.latest_close

        self.donchian_active = (
            self.donchian_regime.active
        )

        self.donchian_recovery = (
            self.donchian_regime.recovery_percent(close)
        )

        self.donchian_recovered = (
            self.donchian_regime.active
            and
            self.donchian_recovery >= self.profile.donchian_recovery
        )

        self.donchian_timeout = (
            self.donchian_regime.active
            and
            self.donchian_regime.days_active >= self.profile.donchian_timeout
        )