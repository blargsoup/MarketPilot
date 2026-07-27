"""
Historical backtesting engine.
"""

from .context import BacktestContext
from .history_slice import slice_market
from .simulation_result import SimulationResult
from .backtest_result import BacktestResult

from marketpilot.market import MarketCalendar
from marketpilot.portfolio import Portfolio


class BacktestEngine:

    def run(
        self,
        market,
        strategy,
    ) -> BacktestResult:

        calendar = MarketCalendar.from_market(
            market,
        )

        portfolio = Portfolio()

        simulations = []

        for index, date in enumerate(calendar):

            context = BacktestContext(

                current_date=date,

                current_index=index,

                total_days=len(calendar),

            )

            snapshot = slice_market(

                market,

                date,

            )

            #
            # Imported here to avoid a circular
            # dependency during startup.
            #

            from marketpilot.signals import SignalEngine

            signals = SignalEngine(
                snapshot,
            )

            result = strategy.evaluate(

                portfolio.current_state,

                signals,

            )

            portfolio.update(

                date,

                snapshot,

                result,

            )

            simulations.append(

                SimulationResult(

                    context=context,

                    market=snapshot,

                    signals=signals,

                    strategy=result,

                )

            )

        return BacktestResult(
            simulations=simulations,
            trades=portfolio.trades,
            equity_curve=portfolio.equity_curve,
        )