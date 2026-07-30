"""
Portfolio simulation.

The portfolio is responsible for tracking portfolio value over time.

The strategy decides WHICH RISK LEVEL to hold.

The StrategyProfile determines WHICH ETF represents that risk level.

This separation allows the exact same strategy to run on:

    NASDAQ
    Semiconductors
    S&P500
    Technology
    Future custom profiles

without changing any strategy logic.
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

        #
        # Strategy profile (NASDAQ, Semiconductor, etc.)
        #

        self.profile = profile

        #
        # Current portfolio value
        #

        self.equity = starting_value

        #
        # Current state
        #

        self.current_state = initial_state

        #
        # Actual ETF currently owned.
        #
        # This will normally be:
        #
        #   Aggressive -> profile.aggressive_asset
        #   Moderate   -> profile.moderate_asset
        #   Defensive  -> DefensiveSelector result
        #

        self.current_symbol = profile.asset_for_state(
            initial_state
        )

        #
        # Previous day's closing price.
        #
        # Used to calculate daily return.
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
        Change portfolio allocation.

        If symbol is omitted, use the StrategyProfile mapping.

        Defensive positions may override this by supplying the
        selected defensive ETF.
        """

        self.current_state = new_state

        if symbol is None:

            self.current_symbol = (
                self.profile.asset_for_state(
                    new_state
                )
            )

        else:

            self.current_symbol = symbol

        #
        # Force tomorrow's return calculation to begin from
        # today's closing price.
        #

        self.previous_close = None

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
        """

        history = market[
            self.current_symbol
        ]

        #
        # Current closing price.
        #

        close = history.latest_close

        #
        # First day holding this asset.
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
        # Record equity curve.
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