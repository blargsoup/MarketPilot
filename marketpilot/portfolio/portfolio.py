"""
Portfolio simulation.

The portfolio is responsible for tracking portfolio value over time.

Strategy decisions are made using the current day's closing data.

A position change generated at EOD is executed for the NEXT trading day.

Therefore:

    Day T close
        ↓
    Evaluate strategy
        ↓
    Generate transition
        ↓
    Queue new position
        ↓
    Day T+1 close
        ↓
    Apply T → T+1 return of the new position

This prevents look-ahead bias.
"""

from __future__ import annotations

from marketpilot.strategies import (
    PortfolioState,
)

from .equity_point import EquityPoint


class Portfolio:

    """
    Simulates portfolio value throughout a backtest.
    """

    ####################################################################
    # Construction
    ####################################################################

    def __init__(
        self,
        profile,
        starting_value: float = 100000.0,
        initial_state: PortfolioState = PortfolioState.AGGRESSIVE,
    ):

        self.profile = profile

        #
        # Current portfolio value.
        #

        self.equity = starting_value

        #
        # Position currently held for the day's return.
        #

        self.current_state = initial_state

        self.current_symbol = profile.asset_for_state(
            initial_state
        )

        #
        # Position that will become active on the NEXT trading day.
        #
        # A strategy transition generated at today's EOD goes here.
        #

        self.pending_state = None
        self.pending_symbol = None

        #
        # Previous closing price of the currently held position.
        #

        self.previous_close = None

        #
        # Equity history.
        #

        self.curve: list[EquityPoint] = []

    ####################################################################
    # Position Changes
    ####################################################################

    def change_position(
        self,
        new_state: PortfolioState,
        symbol: str | None = None,
    ):

        """
        Queue a position change for the next trading day.

        IMPORTANT:

        This does NOT immediately change the position used for today's
        return.

        The strategy is evaluated at today's close, so the resulting
        position begins earning returns tomorrow.
        """

        self.pending_state = new_state

        if symbol is None:

            self.pending_symbol = (
                self.profile.asset_for_state(
                    new_state
                )
            )

        else:

            self.pending_symbol = symbol

    ####################################################################
    # Activate Pending Position
    ####################################################################

    def _activate_pending_position(self):

        """
        Move a queued EOD transition into the active position.

        Called at the START of the next trading day.
        """

        if self.pending_state is None:

            return

        self.current_state = self.pending_state

        self.current_symbol = self.pending_symbol

        #
        # The first price used for the new position is tomorrow's close.
        #
        # There is deliberately no return calculated against today's
        # closing price here.
        #

        self.previous_close = None

        self.pending_state = None
        self.pending_symbol = None

    ####################################################################
    # Daily Update
    ####################################################################

    def update(
        self,
        date,
        market,
    ):

        """
        Update portfolio for one trading day.

        The active position earns today's return.

        Any position queued by yesterday's EOD strategy evaluation
        becomes active before today's return is calculated.
        """

        #
        # First activate yesterday's EOD decision.
        #

        self._activate_pending_position()

        #
        # Get today's closing price for the position being held today.
        #

        history = market[
            self.current_symbol
        ]

        close = history.latest_close

        #
        # First day holding this asset.
        #
        # We establish today's close as the baseline.
        #

        if self.previous_close is None:

            self.previous_close = close

        else:

            daily_return = (
                close
                / self.previous_close
            )

            self.equity *= daily_return

            self.previous_close = close

        #
        # Record today's equity.
        #

        self.curve.append(

            EquityPoint(

                date=date,

                equity=self.equity,

                state=self.current_state,

            )

        )

    ####################################################################
    # Properties
    ####################################################################

    @property
    def equity_curve(self):

        return self.curve

    @property
    def ending_value(self):

        return self.equity

    @property
    def current_asset(self):

        return self.current_symbol

    @property
    def pending_asset(self):

        return self.pending_symbol