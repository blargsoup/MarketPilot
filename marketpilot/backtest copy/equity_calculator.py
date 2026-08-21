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

            prices = market[symbol].close

            available = prices.loc[
                prices.index <= simulation.context.current_date
            ]

            if available.empty:
                continue

            close = available.iloc[-1]

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
            previous_symbol = symbol

        return curve