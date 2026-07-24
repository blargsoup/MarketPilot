"""
Generic historical backtesting engine.
"""

from .context import BacktestContext
from .history_slice import slice_market
from .simulation_result import SimulationResult
from .backtest_result import BacktestResult
from .trade import Trade

from marketpilot.strategies import (
    PortfolioState,
)


class BacktestEngine:

    def run(
        self,
        market,
        strategy,
    ) -> BacktestResult:

        current_state = PortfolioState.TQQQ

        qqq = market["QQQ"]

        dates = qqq.close.index

        simulations = []

        trades = []

        for index, date in enumerate(dates):

            context = BacktestContext(
                current_date=date,
                current_index=index,
                total_days=len(dates),
            )

            market_snapshot = slice_market(
                market,
                index,
            )

            from marketpilot.signals import SignalEngine

            signals = SignalEngine(
                market_snapshot,
            )

            result = strategy.evaluate(
                current_state,
                signals,
            )

            if result.changed:

                trades.append(

                    Trade(

                        date=date,

                        from_state=current_state,

                        to_state=result.new_state,

                        reason=list(result.reasons),

                    )

                )

                current_state = result.new_state

            simulations.append(

                SimulationResult(

                    context=context,

                    market=market_snapshot,

                    signals=signals,

                    strategy=result,

                )

            )

        return BacktestResult(

            simulations=simulations,

            trades=trades,

        )