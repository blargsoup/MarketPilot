"""
A-RVol Version 3

State machine implementation.
"""

from .base import Strategy

from .parameters import ARVolParameters
from .result import StrategyResult
from .state import PortfolioState


class ARVolStrategy(Strategy):

    def __init__(
        self,
        parameters=None,
    ):

        self.parameters = (
            parameters
            or ARVolParameters()
        )

    def evaluate(
        self,
        current_state,
        signals,
    ):

        reasons = []

        #
        # TQQQ -> QLD
        #

        if current_state == PortfolioState.TQQQ:

            if signals.rvol_over_qld:

                reasons.append("RVol >18%")

            if signals.vr_over_qld:

                reasons.append("VR >1.25")

            if signals.spy_breakdown:

                reasons.append("SPY < -3%")

            if reasons:

                return StrategyResult(
                    current_state,
                    PortfolioState.QLD,
                    True,
                    reasons,
                )

        #
        # QLD -> Defensive
        #

        if current_state == PortfolioState.QLD:

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
            # Recovery to TQQQ
            #

            if (
                signals.rvol_clear
                and signals.vr_clear
                and signals.spy_clear
            ):

                return StrategyResult(
                    current_state,
                    PortfolioState.TQQQ,
                    True,
                    [
                        "All Clear",
                    ],
                )

        #
        # Defensive -> QLD
        #

        if current_state == PortfolioState.DEFENSIVE:

            if (
                signals.rvol_defensive_clear
                and signals.vr_defensive_clear
                and signals.spy_recovery
            ):

                return StrategyResult(
                    current_state,
                    PortfolioState.QLD,
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