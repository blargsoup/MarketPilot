"""
A-RVol Version 3

First implementation.

This version only evaluates the
TQQQ -> QLD transition.

Additional transitions will be
added incrementally.
"""

from .parameters import ARVolParameters
from .result import StrategyResult
from .state import PortfolioState


class ARVolStrategy:

    def __init__(
        self,
        parameters=None,
    ):

        self.parameters = (
            parameters
            or ARVolParameters()
        )

    def evaluate(self, signals):

        reasons = []

        move_to_qld = False

        # RVol trigger
        if signals.rvol > self.parameters.rvol_to_qld:

            reasons.append(
                f"✓ RVol {signals.rvol * 100:.2f}% > "
                f"{self.parameters.rvol_to_qld * 100:.2f}%"
            )

            move_to_qld = True

        else:

            reasons.append(
                f"✗ RVol {signals.rvol * 100:.2f}% <= "
                f"{self.parameters.rvol_to_qld * 100:.2f}%"
            )

        # VR trigger
        if signals.vr > self.parameters.vr_to_qld:

            reasons.append(
                f"✓ VR {signals.vr:.2f} > "
                f"{self.parameters.vr_to_qld:.2f}"
            )

            move_to_qld = True

        else:

            reasons.append(
                f"✗ VR {signals.vr:.2f} <= "
                f"{self.parameters.vr_to_qld:.2f}"
            )

        # SPY trigger
        if signals.spy_distance < self.parameters.spy_to_qld:

            reasons.append(
                f"✓ SPY {signals.spy_distance:.2f}% < "
                f"{self.parameters.spy_to_qld:.2f}%"
            )

            move_to_qld = True

        else:

            reasons.append(
                f"✗ SPY {signals.spy_distance:.2f}% >= "
                f"{self.parameters.spy_to_qld:.2f}%"
            )

        state = (
            PortfolioState.QLD
            if move_to_qld
            else PortfolioState.TQQQ
        )

        return StrategyResult(
            state=state,
            reasons=reasons,
        )