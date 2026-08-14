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

IMPORTANT:

Portfolio wealth is calculated from an asset's economic return series.

For synthetic leveraged ETFs produced by LeveragedETFProvider, the
DataFrame contains a NAV column. NAV represents the economic value of
the synthetic investment and is completely independent of share-price
denomination and stock splits.

Therefore:

    Synthetic ETF:
        portfolio return = NAV[t] / NAV[t-1]

    Normal asset:
        portfolio return = Close[t] / Close[t-1]

A split must NEVER create or destroy portfolio wealth.
"""

from __future__ import annotations

import math

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
        # Previous economic value of the currently held position.
        #
        # IMPORTANT:
        #
        # This is NOT necessarily the previous closing share price.
        #
        # For synthetic leveraged ETFs this will be NAV.
        #
        self.previous_value = None

        #
        # Track which economic value column is being used.
        #
        self.previous_value_column = None

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
        # The first economic value used for the new position is
        # tomorrow's value.
        #
        # There is deliberately no return calculated against today's
        # closing value here.
        #
        self.previous_value = None
        self.previous_value_column = None

        self.pending_state = None
        self.pending_symbol = None

    ####################################################################
    # Market Data Helpers
    ####################################################################

    def _has_price(
        self,
        market,
        symbol,
    ):

        """
        Return True if the asset has valid historical data available
        for the current backtest date.
        """

        if symbol not in market.keys():

            return False

        history = market[symbol]

        if history.data.empty:

            return False

        return True

    def _economic_value(
        self,
        history,
    ):
        """
        Return the economic value used for portfolio wealth accounting.

        Synthetic leveraged ETF histories contain a NAV column.

        NAV is authoritative for portfolio wealth because it represents
        the economic value of the synthetic investment independent of
        share-price denomination and stock splits.

        Normal market histories do not contain NAV, so Close is used.

        Returns:

            tuple[value, column_name]
        """

        data = history.data

        #
        # --------------------------------------------------------------
        # Synthetic / NAV-backed asset
        # --------------------------------------------------------------
        #

        if "NAV" in data.columns:

            value = data["NAV"].iloc[-1]

            try:

                value = float(value)

            except (
                TypeError,
                ValueError,
            ):

                value = float("nan")

            if (
                math.isfinite(value)
                and value > 0
            ):

                return (
                    value,
                    "NAV",
                )

        #
        # --------------------------------------------------------------
        # Normal asset
        # --------------------------------------------------------------
        #

        value = history.latest_close

        try:

            value = float(value)

        except (
            TypeError,
            ValueError,
        ):

            value = float("nan")

        if (
            not math.isfinite(value)
            or value <= 0
        ):

            raise ValueError(
                f"Invalid economic value for "
                f"{history.symbol}: {value}"
            )

        return (
            value,
            "Close",
        )

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
        # Get today's data for the position being held today.
        #

        if not self._has_price(
            market,
            self.current_symbol,
        ):

            #
            # The current asset did not exist yet.
            #
            # Do not attempt to calculate a return from an empty
            # history.
            #

            self.curve.append(

                EquityPoint(

                    date=date,

                    equity=self.equity,

                    state=self.current_state,

                )

            )

            return

        history = market[
            self.current_symbol
        ]

        #
        # --------------------------------------------------------------
        # Get economic value.
        # --------------------------------------------------------------
        #

        current_value, value_column = (
            self._economic_value(
                history
            )
        )

        #
        # --------------------------------------------------------------
        # First day holding this asset.
        # --------------------------------------------------------------
        #
        # We establish today's economic value as the baseline.
        #
        # No return is generated on the entry day.
        #

        if self.previous_value is None:

            self.previous_value = current_value
            self.previous_value_column = value_column

        else:

            #
            # Normally the value column remains the same for the
            # lifetime of a position.
            #
            # If the source changes representation, reset the baseline
            # rather than accidentally creating a synthetic return.
            #

            if (
                self.previous_value_column
                != value_column
            ):

                self.previous_value = current_value
                self.previous_value_column = value_column

            else:

                #
                # Calculate the economic growth factor.
                #
                # This is intentionally a GROSS return factor:
                #
                #   1.05 = +5%
                #   0.95 = -5%
                #
                daily_growth = (
                    current_value
                    / self.previous_value
                )

                if (
                    not math.isfinite(
                        daily_growth
                    )
                    or daily_growth <= 0
                ):

                    raise ValueError(
                        f"Invalid daily growth factor "
                        f"for {self.current_symbol} "
                        f"on {date}: "
                        f"{daily_growth}"
                    )

                #
                # Apply economic growth to portfolio wealth.
                #
                self.equity *= daily_growth

                #
                # Advance baseline.
                #

                self.previous_value = current_value

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