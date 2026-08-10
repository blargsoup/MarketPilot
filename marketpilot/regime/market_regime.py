"""
Market regime state.

Tracks long-lived market conditions that persist across trading days.

Unlike indicators, which describe the market today, a MarketRegime
contains memory. This allows strategies to react differently depending
on what has happened previously.

Examples

    - SPY trend armed
    - Bull market confirmed
    - Bear market confirmed
    - Recovery in progress

Initially only the SPY arming logic used by A-RVol V3 is implemented.
"""

from dataclasses import dataclass


@dataclass
class MarketRegime:

    #
    # Has SPY previously broken below the
    # breakdown threshold?
    #

    armed: bool = False

    #
    # Has the strategy been permitted to
    # re-enter risk assets?
    #

    risk_enabled: bool = True

    def update(

        self,

        spy_distance,

        profile,

    ):

        ###############################################################
        # Breakdown arms the regime.
        ###############################################################

        if spy_distance < profile.spy_breakdown:

            self.armed = True

            self.risk_enabled = False

        ###############################################################
        # Recovery enables risk again.
        ###############################################################

        elif (

            self.armed

            and

            spy_distance > profile.spy_recovery

        ):

            self.risk_enabled = True

            self.armed = False