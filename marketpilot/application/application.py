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
    SEMICONDUCTOR_PROFILE,
    SP500_PROFILE
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
)
from marketpilot.diagnostics.strategy_report import StrategyReport


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
                "DEFENSIVE": "TBILL",
            },
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
                    SEMICONDUCTOR_PROFILE,
                ),

                ARVolStrategy(
                    SP500_PROFILE,
                ),

                #
                # Buy & Hold Benchmarks
                #

                BuyAndHoldStrategy(NASDAQ_PROFILE),

                BuyAndHoldStrategy(SEMICONDUCTOR_PROFILE),

                BuyAndHoldStrategy(SP500_PROFILE),

            ],

        )

        benchmark_symbols = ["QQQ", "TQQQ", "SPY", "UPRO", "AVUV"]
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