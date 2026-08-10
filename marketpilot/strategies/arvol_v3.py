"""
A-RVol Version 3

Portfolio state machine.

The strategy decides only between:

    Aggressive
    Moderate
    Defensive

ETF selection is handled entirely by the StrategyProfile.
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

        self.name = f"A-RVol v3 ({profile.name})"

        self.initial_state = PortfolioState.AGGRESSIVE

    def evaluate(
        self,
        current_state,
        signals,
    ):

        reasons = []

        ###############################################################
        # Aggressive -> Moderate
        ###############################################################

        if current_state == PortfolioState.AGGRESSIVE:

            if signals.rvol_over_qld:
                reasons.append(
                    f"RVol > {self.profile.rvol_qld:.2%}"
                )

            if signals.vr_over_qld:
                reasons.append(
                    f"VR > {self.profile.vr_qld:.2f}"
                )

            if signals.spy_breakdown:
                reasons.append(
                    "SPY Breakdown"
                )

            if reasons:

                return StrategyResult(

                    current_state,

                    PortfolioState.MODERATE,

                    True,

                    reasons,

                )

        ###############################################################
        # Moderate -> Defensive
        ###############################################################

        if current_state == PortfolioState.MODERATE:

            if signals.rvol_over_defensive:

                reasons.append(
                    f"RVol > {self.profile.rvol_defensive:.2%}"
                )

            if signals.vr_over_defensive:

                reasons.append(
                    f"VR > {self.profile.vr_defensive:.2f}"
                )

            if signals.spy_breakdown:

                reasons.append(
                    "SPY Breakdown"
                )

            if signals.credit_crisis:

                reasons.append(
                    "Credit Crisis"
                )

            ###########################################################
            # Donchian exit
            #
            # This is specifically a QLD -> Defensive trigger.
            #
            # The Donchian signal is:
            #
            #   QQQ at 40-day low
            #   AND
            #   RVol >= 20%
            #
            # The 18% RVol threshold already handles TQQQ -> QLD,
            # so Donchian is only relevant while already Moderate.
            ###########################################################

            if signals.donchian_confirmed:

                reasons.append(
                    "Donchian"
                )

            if reasons:

                return StrategyResult(

                    current_state,

                    PortfolioState.DEFENSIVE,

                    True,

                    reasons,

                )

            ###########################################################
            # Moderate -> Aggressive
            ###########################################################

            if (

                signals.rvol_clear

                and

                signals.vr_clear

                and

                signals.spy_clear

            ):

                return StrategyResult(

                    current_state,

                    PortfolioState.AGGRESSIVE,

                    True,

                    [

                        "All Clear",

                    ],

                )

        ###############################################################
        # Defensive -> Moderate
        ###############################################################

        if current_state == PortfolioState.DEFENSIVE:

            ###########################################################
            # Donchian-triggered defensive state
            #
            # IMPORTANT:
            #
            # Donchian recovery REPLACES the normal volatility/trend
            # recovery gate.
            #
            # Re-entry occurs when:
            #
            #   1. QQQ recovers 3% from its trailing 5-day low
            #
            # OR
            #
            #   2. 20 trading days have passed.
            #
            # This is intentionally independent of:
            #
            #   RVol
            #   VR
            #   SPY
            #
            # The Donchian exit is a price-based exit, therefore it
            # gets a price-based re-entry.
            ###########################################################

            if signals.donchian_active:

                if signals.donchian_recovered:

                    return StrategyResult(

                        current_state,

                        PortfolioState.MODERATE,

                        True,

                        [

                            "Donchian +3% Recovery",

                        ],

                    )

                if signals.donchian_timeout:

                    return StrategyResult(

                        current_state,

                        PortfolioState.MODERATE,

                        True,

                        [

                            "Donchian 20-Day Timeout",

                        ],

                    )

                #
                # Donchian recovery is active but neither recovery
                # condition has occurred yet.
                #

                return StrategyResult(

                    current_state,

                    current_state,

                    False,

                    [],

                )

            ###########################################################
            # Normal Defensive -> Moderate recovery
            #
            # Used only when the defensive exit was NOT Donchian.
            ###########################################################

            normal_recovery = (

                signals.rvol_defensive_clear

                and

                signals.vr_defensive_clear

                and

                signals.spy_recovery

            )

            if normal_recovery:

                return StrategyResult(

                    current_state,

                    PortfolioState.MODERATE,

                    True,

                    [

                        "Danger Passed",

                    ],

                )

        ###############################################################
        # No transition
        ###############################################################

        return StrategyResult(

            current_state,

            current_state,

            False,

            [],

        )