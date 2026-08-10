"""
Live strategy diagnostics.

The backtest engine records diagnostics as it simulates.
"""

from dataclasses import dataclass

from marketpilot.strategies import PortfolioState


@dataclass
class StrategyDiagnostics:

    #
    # Days spent in each state
    #

    aggressive_days: int = 0
    moderate_days: int = 0
    defensive_days: int = 0

    #
    # Transition counts
    #

    aggressive_to_moderate: int = 0
    moderate_to_aggressive: int = 0
    moderate_to_defensive: int = 0
    defensive_to_moderate: int = 0

    #
    # Moderate → Aggressive gate diagnostics
    #

    moderate_days_checked: int = 0

    passed_rvol: int = 0
    blocked_rvol: int = 0

    passed_vr: int = 0
    blocked_vr: int = 0

    passed_spy: int = 0
    blocked_spy: int = 0

    all_clear: int = 0

    ############################################################

    def record_state(self, state):

        if state == PortfolioState.AGGRESSIVE:
            self.aggressive_days += 1

        elif state == PortfolioState.MODERATE:
            self.moderate_days += 1

        elif state == PortfolioState.DEFENSIVE:
            self.defensive_days += 1

    ############################################################

    def record_transition(self, from_state, to_state):

        if (
            from_state == PortfolioState.AGGRESSIVE
            and
            to_state == PortfolioState.MODERATE
        ):
            self.aggressive_to_moderate += 1

        elif (
            from_state == PortfolioState.MODERATE
            and
            to_state == PortfolioState.AGGRESSIVE
        ):
            self.moderate_to_aggressive += 1

        elif (
            from_state == PortfolioState.MODERATE
            and
            to_state == PortfolioState.DEFENSIVE
        ):
            self.moderate_to_defensive += 1

        elif (
            from_state == PortfolioState.DEFENSIVE
            and
            to_state == PortfolioState.MODERATE
        ):
            self.defensive_to_moderate += 1

    ############################################################

    def record_moderate_gate(self, signals):

        self.moderate_days_checked += 1

        if signals.rvol_clear:
            self.passed_rvol += 1
        else:
            self.blocked_rvol += 1

        if signals.vr_clear:
            self.passed_vr += 1
        else:
            self.blocked_vr += 1

        if signals.spy_clear:
            self.passed_spy += 1
        else:
            self.blocked_spy += 1

        if (
            signals.rvol_clear
            and signals.vr_clear
            and signals.spy_clear
        ):
            self.all_clear += 1