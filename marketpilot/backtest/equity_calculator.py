"""
Simple portfolio simulator.
"""

from .equity_curve import EquityPoint

class EquityCalculator:

    def calculate(
        self,
        backtest,
        market,
        starting_value=100000.0,
    ):

        simulations = backtest.simulations

        curve = []

        cash = starting_value

        shares = 0.0

        current_symbol = None

        for simulation in simulations:

            state = simulation.strategy.new_state

            symbol = state.asset

            print(symbol)
            print(simulation.context.current_date)
            print(market[symbol].close.index[0])
            print(market[symbol].close.index[-1])

            close = market[symbol].close.loc[
                simulation.context.current_date
            ]

            #
            # First day
            #

            if shares == 0:

                shares = cash / close

                cash = 0.0

                current_symbol = symbol

            #
            # Switched ETFs
            #

            elif symbol != current_symbol:

                equity = shares * previous_close

                shares = equity / close

                current_symbol = symbol

            #
            # Current portfolio value
            #

            equity = shares * close

            curve.append(

                EquityPoint(

                    date=simulation.context.current_date,

                    equity=equity,

                    state=state,

                )

            )

            previous_close = close