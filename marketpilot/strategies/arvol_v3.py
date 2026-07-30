"""
A-RVol Version 3

Portfolio state machine.

The strategy knows nothing about ETFs.

It only decides between:

    Aggressive
    Moderate
    Defensive

The StrategyProfile determines which ETFs those
states correspond to.
"""

from .base import Strategy

from .profile import NASDAQ_PROFILE

from .result import StrategyResult

from .state import PortfolioState


class ARVolStrategy(Strategy):

    def __init__(
        self,
        profile=NASDAQ_PROFILE,
    ):

        self.profile = profile

        self.name = (
            f"A-RVol v3 ({profile.name})"
        )

        self.initial_state = (
            PortfolioState.AGGRESSIVE
        )

    def evaluate(

        self,

        current_state,

        signals,

    ):

        reasons = []

        #
        # Aggressive -> Moderate
        #

        if current_state == PortfolioState.AGGRESSIVE:

            if signals.rvol_over_qld:
                reasons.append("RVol >18%")

            if signals.vr_over_qld:
                reasons.append("VR >1.25")

            if signals.spy_breakdown:
                reasons.append("SPY Breakdown")

            if reasons:

                return StrategyResult(

                    current_state,

                    PortfolioState.MODERATE,

                    True,

                    reasons,

                )

        #
        # Moderate -> Defensive
        #

        if current_state == PortfolioState.MODERATE:

            if signals.rvol_over_defensive:
                reasons.append("RVol >36%")

            if signals.vr_over_defensive:
                reasons.append("VR >1.40")

            if signals.spy_breakdown:
                reasons.append("SPY Breakdown")

            if signals.credit_crisis:
                reasons.append("Credit Crisis")

            if signals.donchian_confirmed:
                reasons.append("Donchian")

            if reasons:

                return StrategyResult(

                    current_state,

                    PortfolioState.DEFENSIVE,

                    True,

                    reasons,

                )

            #
            # Recovery
            #

            if (

                signals.rvol_clear

                and signals.vr_clear

                and signals.spy_clear

            ):

                return StrategyResult(

                    current_state,

                    PortfolioState.AGGRESSIVE,

                    True,

                    [

                        "All Clear",

                    ],

                )

        #
        # Defensive -> Moderate
        #

        if current_state == PortfolioState.DEFENSIVE:

            if (

                signals.rvol_defensive_clear

                and signals.vr_defensive_clear

                and signals.spy_recovery

            ):

                return StrategyResult(

                    current_state,

                    PortfolioState.MODERATE,

                    True,

                    [

                        "Danger Passed",

                    ],

                )

        return StrategyResult(

            current_state,

            current_state,

            False,

            [],

        )