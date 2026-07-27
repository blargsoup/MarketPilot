"""
Runs buy-and-hold benchmark simulations.
"""

from types import SimpleNamespace

from .benchmark_result import BenchmarkResult
from marketpilot.performance.drawdown import (
    calculate_drawdown,
)


class BenchmarkRunner:

    def run(
        self,
        market,
        symbols,
        dates,
        starting_value=100000,
    ):

        results = []

        dates = list(dates)

        if len(dates) < 2:
            return results

        years = len(dates) / 252

        for symbol in symbols:

            history = market[symbol]

            closes = history.close.reindex(dates)

            #
            # Skip incomplete histories
            #

            if closes.isna().any() or len(closes) < 2:
                continue

            first = float(closes.iloc[0])
            last = float(closes.iloc[-1])

            shares = starting_value / first

            equity_curve = []

            for date, price in closes.items():

                equity = shares * float(price)

                equity_curve.append(SimpleNamespace(date=date, equity=equity))

            ending = equity_curve[-1].equity

            total_return = (
                ending / starting_value
            ) - 1

            annual_return = (
                (ending / starting_value)
                ** (1 / years)
            ) - 1

            drawdown = calculate_drawdown(
                equity_curve
            )

            results.append(

                BenchmarkResult(

                    symbol=symbol,

                    starting_value=starting_value,

                    ending_value=ending,

                    total_return=total_return,

                    annual_return=annual_return,

                    max_drawdown=drawdown.max_drawdown,

                )

            )

        return results
