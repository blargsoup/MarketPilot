"""
Generic historical backtesting engine.

The engine is responsible for:

    • Iterating through every trading day
    • Creating a MarketView for each day
    • Running the strategy
    • Updating the portfolio
    • Recording trades
    • Returning a BacktestResult
"""

from marketpilot.market import (
    MarketCalendar,
    MarketView,
)

from marketpilot.signals import SignalEngine

from marketpilot.strategies import (
    PortfolioState,
)

from marketpilot.defensive import (
    DefensiveSelector,
)

from marketpilot.portfolio import Portfolio

from .backtest_result import BacktestResult
from .context import BacktestContext
from .simulation_result import SimulationResult
from .trade import Trade


class BacktestEngine:

    def run(
        self,
        market,
        strategy,
    ):

        calendar = MarketCalendar.from_market(
            market
        )

        portfolio = Portfolio(

            profile=strategy.profile,

            initial_state=strategy.initial_state,

        )

        selector = DefensiveSelector()

        current_state = strategy.initial_state

        simulations = []

        trades = []

        for index, date in enumerate(calendar):

            ####################################################
            # Instead of copying history,
            # simply create a view onto today's market.
            ####################################################

            market_view = MarketView(

                market,

                date,

            )

            signals = SignalEngine(

                market_view,

                strategy.profile,

            )

            result = strategy.evaluate(

                current_state,

                signals,

            )

            ####################################################
            # Position change?
            ####################################################

            if result.changed:

                if result.new_state == PortfolioState.DEFENSIVE:

                    defensive = selector.select(
                        market_view
                    )

                    portfolio.change_position(

                        PortfolioState.DEFENSIVE,

                        defensive.symbol,

                    )

                else:

                    portfolio.change_position(

                        result.new_state,

                    )

                trades.append(

                    Trade(

                        date=date,

                        from_state=current_state,

                        to_state=result.new_state,

                        reason=list(result.reasons),

                    )

                )

                current_state = result.new_state

            ####################################################
            # Update portfolio
            ####################################################

            portfolio.update(

                date=date,

                market=market_view,

            )

            simulations.append(

                SimulationResult(

                    context=BacktestContext(

                        current_date=date,

                        current_index=index,

                        total_days=len(calendar),

                    ),

                    market=market_view,

                    signals=signals,

                    strategy=result,

                )

            )

        return BacktestResult(

            simulations=simulations,

            trades=trades,

            equity_curve=portfolio.equity_curve,

            calendar=calendar,

        )