"""
Portfolio simulation.

Owns the portfolio state,
equity, positions and trades.
"""

from .equity_point import EquityPoint

from marketpilot.backtest.trade import Trade

from marketpilot.strategies import (
    ETF_MAP,
    PortfolioState,
)


class Portfolio:

    def __init__(
        self,
        starting_value=100000.0,
        initial_state=PortfolioState.TQQQ,
    ):

        self.equity = starting_value

        self.current_state = initial_state

        self.current_symbol = ETF_MAP[
            self.current_state
        ]

        self.previous_close = None

        self.equity_curve = []

        self.trades = []

    def update(
        self,
        date,
        market,
        strategy_result,
    ):

        #
        # Execute trade
        #

        if strategy_result.changed:

            self.trades.append(

                Trade(

                    date=date,

                    from_state=self.current_state,

                    to_state=strategy_result.new_state,

                    reason=list(
                        strategy_result.reasons
                    ),

                )

            )

            self.current_state = (
                strategy_result.new_state
            )

            self.current_symbol = ETF_MAP[
                self.current_state
            ]

            #
            # Start measuring the
            # new asset tomorrow.
            #

            self.previous_close = None

        close = market[
            self.current_symbol
        ].latest_close

        if self.previous_close is not None:

            daily_return = (
                close / self.previous_close
            ) - 1.0

            self.equity *= (
                1.0 + daily_return
            )

        self.equity_curve.append(

            EquityPoint(

                date=date,

                equity=self.equity,

                state=self.current_state,

            )

        )

        self.previous_close = close
