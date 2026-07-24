"""
Simple portfolio simulator.
"""

from .equity_curve import EquityPoint

from marketpilot.strategies import (
    PortfolioState,
)


ETF_MAP = {

    PortfolioState.TQQQ: "QQQ",

    PortfolioState.QLD: "QQQ",

    PortfolioState.DEFENSIVE: "TLT",

}


class EquityCalculator:

    def calculate(
        self,
        backtest,
        market,
        starting_value=100000.0,
    ):

        simulations = backtest.simulations

        equity = starting_value

        curve = []

        previous_close = None

        previous_symbol = None

        for simulation in simulations:

            state = simulation.strategy.new_state

            symbol = ETF_MAP[state]

            close = (
                market[symbol]
                .close
                .loc[
                    simulation.context.current_date
                ]
            )

            if previous_close is not None:

                daily_return = (
                    close / previous_close
                ) - 1.0

                equity *= (
                    1.0 + daily_return
                )

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