"""
Main MarketPilot application.
"""
import pandas as pd
from marketpilot import __version__
from marketpilot.utils.logger import setup_logger
from marketpilot.utils.config import Config
from marketpilot.data import MarketDataService
from marketpilot.signals import SignalEngine
from marketpilot.strategies import (
    ARVolStrategy,
    BuyAndHoldStrategy,
    PortfolioState,
    NASDAQ_PROFILE,
    NASDAQ_CASH_PROFILE,
    NASDAQ_2STATE_PROFILE,
    NASDAQ_QQQ_PROFILE,
    SEMICONDUCTOR_PROFILE,
    SP500_PROFILE,
    NASDAQ_2STATE_CASH_PROFILE,
    #NASDAQ_2STATE_PSQ_PROFILE,
    NASDAQ_2STATE_SQQQ_PROFILE,
)
from marketpilot.defensive import (
    DefensiveSelector,
)
from marketpilot.reports import ConsoleReport
from marketpilot.models import AnalysisResult
from marketpilot.backtest import BacktestEngine
from marketpilot.backtest.forward_compound import ForwardCompounder
from marketpilot.data import MARKET_UNIVERSE
from marketpilot.statistics import Statistics
from marketpilot.benchmarks import BenchmarkRunner
from marketpilot.performance import PerformanceAnalyzer
from marketpilot.comparison import StrategyComparisonRunner
from marketpilot.regime import (
    MarketRegime,
    DonchianRegime,
)
from marketpilot.indicators import IndicatorEngine
from marketpilot.reports import (
    ConsoleReport,
    DashboardReport,
    TradeReport,
    CheckpointReport,
)
from marketpilot.diagnostics.strategy_report import StrategyReport
from marketpilot.reports import CheckpointReport
from marketpilot.reports import SignalReport
from marketpilot.reports.transition_timing import (
    TransitionTimingAnalyzer,
)

from marketpilot.reports.transition_timing_report import (
    TransitionTimingReport,
)
from marketpilot.reports.transition_analytics import (
    TransitionAnalytics,
)

from marketpilot.reports.transition_analytics_report import (
    TransitionAnalyticsReport,
)

from marketpilot.reports.period_performance import (
    PeriodPerformanceAnalyzer,
)


class Application:

    def __init__(self):

        self.logger = setup_logger()
        self.backtester = BacktestEngine()
        self.comparisons = StrategyComparisonRunner(self.backtester)

        Config()

        self.data = MarketDataService()
        self.strategy = ARVolStrategy()
        self.selector = DefensiveSelector()
        self.report = ConsoleReport(
            self.logger,
        )

    def run(
        self,
        refresh: bool = False,
        backtest: bool = False,
    ):

        logger = self.logger

        symbols = [

            asset.symbol

            for asset in MARKET_UNIVERSE

        ]

        market = self.data.get_histories(
            symbols,
            refresh=refresh,
        )

        #
        # Synthetic leveraged ETF sanity checks.
        #

        if "TQQQ" in market:

            tqqq = market["TQQQ"]

            logger.info("")
            logger.info(
                "Synthetic ETF Validation"
            )
            logger.info(
                "------------------------------"
            )

            logger.info(
                "TQQQ First Date : %s",
                tqqq.first_date,
            )

            logger.info(
                "TQQQ Last Date  : %s",
                tqqq.last_date,
            )

            logger.info(
                "TQQQ Rows       : %d",
                tqqq.rows,
            )

            logger.info(
                "TQQQ First Close: %.6f",
                tqqq.data["Close"].iloc[0],
            )

            logger.info(
                "TQQQ Last Close : %.6f",
                tqqq.data["Close"].iloc[-1],
            )

            logger.info(
                "TQQQ Min Close  : %.6f",
                tqqq.data["Close"].min(),
            )

        #
        # Daily mode
        #

        if not backtest:

            #
            # Calculate today's signals only.
            #

            indicators = IndicatorEngine(

                market,

                self.strategy.profile,

            )

            #
            # Live regime state
            #

            regime = MarketRegime()

            donchian_regime = DonchianRegime()

            signals = SignalEngine(
                market,
                self.strategy.profile,
                regime,
                donchian_regime,
            )

            strategy = self.strategy.evaluate(

                PortfolioState.MODERATE,

                signals,

            )

            defensive = self.selector.select(

                indicators,

                self.strategy.profile,

            )

            DashboardReport(
                self.strategy.profile,
            ).display(

                logger,

                market,

                signals,

                strategy,

                defensive,

                self.strategy.profile,

            )

            return

        #
        # Full backtest only when requested.
        #

        backtest_result = self.backtester.run(
            market,
            self.strategy,
        )

        # ------------------------------------------------------------
        # Forward compounding model
        # ------------------------------------------------------------

        state_series = {
            simulation.context.current_date: simulation.strategy.new_state.name
            for simulation in backtest_result.simulations
        }

        state_series = pd.Series(state_series)

        forward_compounder = ForwardCompounder(
            starting_value=100_000.0,
            state_assets={
                "AGGRESSIVE": "TQQQ",
                "MODERATE": "QLD",
                "DEFENSIVE": "CASH",
            },
            cash_annual_rate=0.02,
        )

        forward_result = forward_compounder.run(
            market=market,
            states=state_series,
        )

        logger.info("")
        logger.info("Forward Compounding Model")
        logger.info("------------------------------")

        logger.info(
            "Starting Value : $%s",
            f"{forward_result.starting_value:,.2f}",
        )

        logger.info(
            "Ending Value   : $%s",
            f"{forward_result.ending_value:,.2f}",
        )

        logger.info(
            "Total Return   : %.2f%%",
            forward_result.total_return * 100,
        )

        logger.info(
            "Annual CAGR    : %.2f%%",
            forward_result.cagr * 100,
        )

        logger.info(
            "Max Drawdown   : %.2f%%",
            forward_result.max_drawdown * 100,
        )

        logger.info(
            "Aggressive Days: %d",
            forward_result.aggressive_days,
        )

        logger.info(
            "Moderate Days  : %d",
            forward_result.moderate_days,
        )

        logger.info(
            "Defensive Days : %d",
            forward_result.defensive_days,
        )

        strategy_comparisons = self.comparisons.run(
            market,
            [
                #
                # A-RVol Profiles
                #

                ARVolStrategy(
                    NASDAQ_PROFILE,
                ),

                ARVolStrategy(
                    NASDAQ_2STATE_PROFILE,
                ),

                ARVolStrategy(
                    NASDAQ_CASH_PROFILE,
                ),

                ARVolStrategy(
                    NASDAQ_QQQ_PROFILE,
                ),

                ARVolStrategy(
                    SEMICONDUCTOR_PROFILE,
                ),

                ARVolStrategy(
                    SP500_PROFILE,
                ),

                ARVolStrategy(
                    NASDAQ_2STATE_CASH_PROFILE,
                ),

                #ARVolStrategy(
                #    NASDAQ_2STATE_PSQ_PROFILE,
                #),

                ARVolStrategy(
                    NASDAQ_2STATE_SQQQ_PROFILE,
                ),

            ],

        )

        checkpoint_report = CheckpointReport()

        checkpoint_path, detailed_checkpoint_path = (
            checkpoint_report.generate(
                strategy_comparisons
            )
        )

        logger.info("")
        logger.info("Checkpoint Analysis")
        logger.info("------------------------------")

        logger.info(
            "Compact CSV   : %s",
            checkpoint_path,
        )

        logger.info(
            "Detailed CSV  : %s",
            detailed_checkpoint_path,
        )

        # ------------------------------------------------------------
        # Signal analytics
        # ------------------------------------------------------------

        signal_report = SignalReport()

        signal_paths = signal_report.generate(
            strategy_comparisons,
            market,
        )

        signal_events_path = signal_paths["signal_events"]

        signal_events = pd.read_csv(
            signal_events_path,
        )

        logger.info(
            "Loaded signal event history: %s",
            signal_events_path,
        )

        logger.info("")
        logger.info("Signal analytics exported:")

        for name, path in signal_paths.items():
            logger.info(
                "    %-24s %s",
                name,
                path,
            )

        # ------------------------------------------------------------
        # Benchmark calculations
        #
        # Use the existing benchmark engine for non-leveraged assets.
        # Leveraged ETFs are handled separately because their historical
        # performance must be modeled using daily leveraged returns rather
        # than reconstructed historical prices.
        # ------------------------------------------------------------

        benchmark_symbols = ["QQQ", "SPY", "AVUV"]

        backtest_result.benchmarks = BenchmarkRunner().run(
            market,
            benchmark_symbols,
            (point.date for point in backtest_result.equity_curve),
        )

        latest = backtest_result.simulations[-1]

        logger.info("")
        logger.info("Latest Simulation")
        logger.info("------------------------------")

        logger.info(
            "State : %s",
            latest.strategy.new_state.name,
        )

        logger.info(
            "RVol : %.2f%%",
            latest.signals.rvol * 100,
        )

        logger.info(
            "VR : %.2f",
            latest.signals.vr,
        )

        logger.info("")
        logger.info(
            "Backtest Timeline : %d trading days",
            backtest_result.total_days
        )

        logger.info(
            "First Simulation : %s",
            backtest_result.simulations[0].context.current_date,
        )

        logger.info(
            "Last Simulation  : %s",
            backtest_result.simulations[-1].context.current_date,
        )

        signals = latest.signals

        indicators = IndicatorEngine(

            market,

            self.strategy.profile,

        )

        defensive = self.selector.select(

            indicators,

            self.strategy.profile,

        )

        result = latest.strategy

        statistics = PerformanceAnalyzer().analyze(
            backtest_result
        )

        analysis = AnalysisResult(
            market=market,
            signals=signals,
            strategy=result,
            defensive=defensive,
            backtest=backtest_result,
            statistics=statistics,
        )

        analysis.strategy_comparisons = strategy_comparisons

        self.report.display(
            analysis,
        )

        TradeReport().display(

            logger,

            backtest_result,

        )

        StrategyReport().display(

            logger,

            backtest_result.diagnostics,

        )

        # ------------------------------------------------------------
        # Transition timing analytics
        # ------------------------------------------------------------

        timing_analyzer = TransitionTimingAnalyzer()

        timing_report = TransitionTimingReport()

        logger.info("")
        logger.info("Transition Timing Analytics")
        logger.info("------------------------------")

        for comparison in strategy_comparisons:

            #
            # Strategy identity
            #

            name = comparison.name

            safe_name = (
                name
                .lower()
                .replace(" ", "_")
                .replace("/", "_")
                .replace("(", "")
                .replace(")", "")
            )

            logger.info(
                "Analyzing transition timing: %s",
                name,
            )

            #
            # Build state history from the actual backtest.
            #
            # This is important: we want the states that the strategy
            # actually entered during its backtest, not states reconstructed
            # from today's signals.
            #

            states = pd.Series(
                {
                    simulation.context.current_date:
                        simulation.strategy.new_state.name
                    for simulation
                    in comparison.backtest.simulations
                }
            )

            #
            # Use the exact asset mapping from this strategy's profile.
            #
            # This makes the same analyzer work for:
            #
            #   NASDAQ
            #   NASDAQ 2-State
            #   NASDAQ 2-State Cash
            #   NASDAQ 2-State SQQQ
            #   NASDAQ QQQ Moderate
            #   S&P 500
            #   Semiconductors
            #

            profile = comparison.profile

            state_assets = {
                "AGGRESSIVE": profile.aggressive_asset,
                "MODERATE": profile.moderate_asset,
                "DEFENSIVE": (
                    profile.defensive_assets[0]
                    if profile.defensive_assets
                    else profile.cash_asset
                ),
            }

            #
            # Generate transition-level analytics.
            #

            transitions = timing_analyzer.analyze(
                market,
                states,
                state_assets,
            )

            #
            # Detailed transition CSV.
            #

            timing_path = timing_report.generate(
                transitions,
                filename=f"transition_timing_{safe_name}.csv",
            )

            #
            # Aggregate timing summary.
            #

            summaries = timing_analyzer.summarize(
                transitions,
            )

            summary_path = timing_report.generate_summary(
                summaries,
                output_path=f"output/transition_timing_summary_{safe_name}.csv"
            )

            logger.info(
                "  Detailed : %s",
                timing_path,
            )

            logger.info(
                "  Summary  : %s",
                summary_path,
            )

        # ------------------------------------------------------------
        # Aggregate transition analytics
        # ------------------------------------------------------------

        transition_analytics = (
            TransitionAnalytics()
        )

        transition_analytics_report = (
            TransitionAnalyticsReport()
        )

        period_performance = (
            PeriodPerformanceAnalyzer()
        )

        all_transition_aggregates = []
        all_period_performance = []

        logger.info("")
        logger.info(
            "Aggregate Transition Analytics"
        )
        logger.info(
            "------------------------------"
        )

        for comparison in strategy_comparisons:

            name = comparison.name

            safe_name = (
                name
                .lower()
                .replace(" ", "_")
                .replace("/", "_")
                .replace("(", "")
                .replace(")", "")
            )

            #
            # Rebuild the exact state history used above.
            #

            states = pd.Series(
                {
                    simulation.context.current_date:
                        simulation.strategy.new_state.name
                    for simulation
                    in comparison.backtest.simulations
                }
            )

            profile = comparison.profile

            state_assets = {
                "AGGRESSIVE":
                    profile.aggressive_asset,

                "MODERATE":
                    profile.moderate_asset,

                "DEFENSIVE":
                    (
                        profile.defensive_assets[0]
                        if profile.defensive_assets
                        else profile.cash_asset
                    ),
            }

            #
            # Generate transition objects.
            #

            transitions = (
                timing_analyzer.analyze(
                    market,
                    states,
                    state_assets,
                )
            )

            #
            # Full + historical-period transition aggregates.
            #

            aggregates = transition_analytics.analyze_periods(
                transitions,
                strategy_name=name,
                profile=comparison.profile,
            )

            all_transition_aggregates.extend(
                aggregates
            )

            #
            # Performance by historical period.
            #

            performance = (
                period_performance.analyze(
                    comparison
                )
            )

            all_period_performance.extend(
                performance
            )

            logger.info(
                "  %s",
                name,
            )

            for aggregate in aggregates:

                logger.info(
                    "    %-12s "
                    "Transitions=%4d "
                    "Whipsaws=%3d "
                    "Exit=%.2f%% "
                    "Re-entry=%.2f%% "
                    "Defensive=%.1fd",
                    aggregate.period,
                    aggregate.transitions,
                    aggregate.whipsaws,
                    (
                        aggregate.average_exit_timing
                        * 100
                        if aggregate.average_exit_timing
                        is not None
                        else 0
                    ),
                    (
                        aggregate.average_reentry_timing
                        * 100
                        if aggregate.average_reentry_timing
                        is not None
                        else 0
                    ),
                    (
                        aggregate.average_defensive_duration
                        if aggregate.average_defensive_duration
                        is not None
                        else 0
                    ),
                )

        #
        # Transition analytics CSV.
        #

        transition_analytics_path = (
            transition_analytics_report.generate(
                all_transition_aggregates,
                filename=(
                    "transition_analytics.csv"
                ),
            )
        )

        #
        # Period performance CSV.
        #

        period_rows = [
            {
                "Strategy": p.strategy,
                "Period": p.period,
                "Start Date": p.start_date,
                "End Date": p.end_date,
                "Starting Equity": p.starting_equity,
                "Ending Equity": p.ending_equity,
                "Total Return": p.total_return,
                "CAGR": p.cagr,
                "Max Drawdown": p.max_drawdown,
                "Trades": p.trades,
            }
            for p in all_period_performance
        ]

        period_performance_path = ("output/performance_periods.csv")
        

        pd.DataFrame(
            period_rows
        ).to_csv(
            period_performance_path,
            index=False,
        )

        logger.info("")
        logger.info(
            "Aggregate analytics:"
        )
        logger.info(
            "    %s",
            transition_analytics_path,
        )
        logger.info(
            "    %s",
            period_performance_path,
        )
        

        logger.info("")
        logger.info("Historical Checkpoints")
        logger.info("------------------------------")

        logger.info(
            "CSV exported to:"
        )

        logger.info(
            "    %s",
            checkpoint_path,
        )

        logger.info("")
        logger.info("Historical Checkpoints")
        logger.info("------------------------------")

        logger.info(
            "CSV exported to:"
        )

        logger.info(
            "    %s",
            checkpoint_path,
        )