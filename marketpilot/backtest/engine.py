"""
Generic historical backtesting engine.

Responsible for:

    • Iterating trading days
    • Building market snapshots
    • Updating market regime
    • Evaluating strategy
    • Updating portfolio
    • Recording trades
    • Producing the BacktestResult
"""

from marketpilot.market import (
    MarketCalendar,
    MarketView,
)
from marketpilot.regime import (
    MarketRegime,
    DonchianRegime,
)
from marketpilot.signals import SignalEngine
from marketpilot.strategies import (
    PortfolioState,
)
from marketpilot.defensive import (
    DefensiveSelector,
)
from marketpilot.portfolio import (
    Portfolio,
)
from .backtest_result import BacktestResult
from .context import BacktestContext
from .simulation_result import SimulationResult
from .trade import Trade
from marketpilot.indicators import (
    IndicatorEngine,
)
from marketpilot.diagnostics import StrategyDiagnostics


class BacktestEngine:

    def run(
        self,
        market,
        strategy,
    ) -> BacktestResult:

        diagnostics = StrategyDiagnostics()

        #
        # Assets required for strategy calculations.
        #
        # These determine the historical backtest calendar.
        #
        # Optional assets such as SGOV, AVUV, etc. must not shorten
        # the available backtest history.
        #
        # Remove duplicates while preserving order.
        #

        required_symbols = [
            strategy.profile.signal_asset,
            strategy.profile.trend_asset,
            strategy.profile.aggressive_asset,
            strategy.profile.moderate_asset,
            strategy.profile.cash_asset,
        ]

        required_symbols = list(
            dict.fromkeys(required_symbols)
        )

        calendar = MarketCalendar.from_market(
            market,
            required_symbols=required_symbols,
        )

        portfolio = Portfolio(
            profile=strategy.profile,
            initial_state=strategy.initial_state,
        )

        selector = DefensiveSelector()

        #
        # Persistent regimes.
        #

        regime = MarketRegime()

        donchian_regime = DonchianRegime()

        current_state = strategy.initial_state

        simulations = []

        trades = []

        for index, date in enumerate(calendar):

            ###############################################################
            # Historical market snapshot.
            ###############################################################

            market_view = MarketView(
                market,
                date,
            )

            ###############################################################
            # Signal asset close.
            ###############################################################

            signal_close = market_view[
                strategy.profile.signal_asset
            ].latest_close

            ###############################################################
            # Donchian recovery update
            #
            # IMPORTANT:
            #
            # If the Donchian regime was already active BEFORE today's
            # EOD decision, today's close is a recovery-day observation.
            #
            # This happens BEFORE SignalEngine is created so that today's
            # EOD close can participate in today's recovery decision.
            #
            # If the regime is activated by today's decision, it is NOT
            # updated here. Today's trigger close is the exit reference,
            # not a recovery day.
            ###############################################################

            donchian_was_active = donchian_regime.active

            if donchian_was_active:

                donchian_regime.update(
                    index,
                    signal_close,
                )

            ###############################################################
            # Indicators.
            ###############################################################

            indicators = IndicatorEngine(
                market_view,
                strategy.profile,
            )

            ###############################################################
            # Signals.
            ###############################################################

            signals = SignalEngine(
                market_view,
                strategy.profile,
                regime,
                donchian_regime,
            )

            ###############################################################
            # Diagnostics
            ###############################################################

            diagnostics.record_state(current_state)

            if current_state == PortfolioState.MODERATE:

                diagnostics.record_moderate_gate(
                    signals,
                )

            ###############################################################
            # Update SPY regime.
            ###############################################################

            regime.update(
                signals.spy_distance,
                strategy.profile,
            )

            ###############################################################
            # Strategy decision.
            ###############################################################

            result = strategy.evaluate(
                current_state,
                signals,
            )

            ###############################################################
            # Execute transition.
            ###############################################################

            if result.changed:

                ###########################################################
                # Donchian regime activation.
                #
                # This happens AFTER today's strategy decision.
                #
                # Therefore today's trigger-day close does NOT become
                # recovery day 1.
                ###########################################################

                if (
                    current_state
                    == PortfolioState.MODERATE

                    and

                    result.new_state
                    == PortfolioState.DEFENSIVE

                    and

                    signals.donchian_confirmed
                ):

                    donchian_regime.activate(
                        index,
                    )

                ###########################################################
                # Leaving Defensive clears Donchian recovery regime.
                ###########################################################

                if (
                    current_state
                    == PortfolioState.DEFENSIVE

                    and

                    result.new_state
                    != PortfolioState.DEFENSIVE
                ):

                    donchian_regime.clear()

                ###########################################################
                # Portfolio transition.
                ###########################################################

                from_symbol = portfolio.current_symbol

                if result.new_state == PortfolioState.DEFENSIVE:

                    defensive = selector.select(
                        indicators,
                        strategy.profile,
                    )

                    to_symbol = defensive.symbol

                    portfolio.change_position(
                        PortfolioState.DEFENSIVE,
                        to_symbol,
                    )

                else:

                    to_symbol = strategy.profile.asset_for_state(
                        result.new_state,
                    )

                    portfolio.change_position(
                        result.new_state,
                    )

                ###########################################################
                # Record trade.
                ###########################################################

                trades.append(
                    Trade(
                        date=date,
                        from_state=current_state,
                        to_state=result.new_state,
                        from_symbol=from_symbol,
                        to_symbol=to_symbol,
                        reason=list(result.reasons),
                    )
                )

                diagnostics.record_transition(
                    current_state,
                    result.new_state,
                )

                current_state = result.new_state

            ###############################################################
            # Portfolio valuation.
            ###############################################################

            portfolio.update(
                date=date,
                market=market_view,
            )

            ###############################################################
            # Daily snapshot.
            ###############################################################

            context = BacktestContext(
                current_date=date,
                current_index=index,
                total_days=len(calendar),
            )

            simulations.append(
                SimulationResult(
                    context=context,
                    market=market_view,
                    signals=signals,
                    strategy=result,
                    portfolio_state=current_state,
                    symbol=portfolio.current_symbol,
                    equity=portfolio.equity_curve[-1].equity,
                )
            )

        ###################################################################
        # Finished.
        ###################################################################

        backtest = BacktestResult(
            simulations=simulations,
            trades=trades,
            equity_curve=portfolio.equity_curve,
            calendar=calendar,
        )

        backtest.diagnostics = diagnostics

        return backtest