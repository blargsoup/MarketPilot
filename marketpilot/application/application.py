"""
Main MarketPilot application.
"""

from marketpilot import __version__

from marketpilot.utils.logger import setup_logger
from marketpilot.utils.config import Config
from marketpilot.data import MarketDataService
from marketpilot.signals import SignalEngine
from marketpilot.strategies import (
    ARVolStrategy,
    BuyAndHoldStrategy,
    PortfolioState,
)
from marketpilot.defensive import (
    DefensiveSelector,
)
from marketpilot.reports import ConsoleReport
from marketpilot.models import AnalysisResult
from marketpilot.backtest import BacktestEngine
from marketpilot.data import MARKET_UNIVERSE
from marketpilot.statistics import Statistics
from marketpilot.benchmarks import BenchmarkRunner
from marketpilot.performance import PerformanceAnalyzer
from marketpilot.comparison import StrategyComparisonRunner

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

    def run(self):

        logger = self.logger

        symbols = [

            asset.symbol

            for asset in MARKET_UNIVERSE

        ]

        market = self.data.get_histories(symbols)

        backtest = self.backtester.run(
            market,
            self.strategy,
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

                BuyAndHoldStrategy(
                    PortfolioState.AGGRESSIVE,
                    NASDAQ_PROFILE,
                ),

                BuyAndHoldStrategy(
                    PortfolioState.AGGRESSIVE,
                    SEMICONDUCTOR_PROFILE,
                ),

                BuyAndHoldStrategy(
                    PortfolioState.AGGRESSIVE,
                    SP500_PROFILE,
                ),

            ],

        )

        benchmark_symbols = ["QQQ", "TQQQ", "SPY", "UPRO", "AVUV"]
        backtest.benchmarks = BenchmarkRunner().run(
            market,
            benchmark_symbols,
            (point.date for point in backtest.equity_curve),
        )

        latest = backtest.simulations[-1]

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
            backtest.total_days
        )

        logger.info(
            "First Simulation : %s",
            backtest.simulations[0].context.current_date,
        )

        logger.info(
            "Last Simulation  : %s",
            backtest.simulations[-1].context.current_date,
        )

        signals = SignalEngine(
            market,
            self.strategy.profile,
        )


        defensive = self.selector.select(
            market,
        )

        result = self.strategy.evaluate(
            PortfolioState.TQQQ,
            signals,
        )

        statistics = PerformanceAnalyzer().analyze(
            backtest
        )

        analysis = AnalysisResult(
            market=market,
            signals=signals,
            strategy=result,
            defensive=defensive,
            backtest=backtest,
            statistics=statistics,
        )

        analysis.strategy_comparisons = strategy_comparisons

        self.report.display(
            analysis,
        )
