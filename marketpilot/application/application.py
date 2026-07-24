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
    PortfolioState,
)
from marketpilot.defensive import (
    DefensiveSelector,
)
from marketpilot.reports import ConsoleReport
from marketpilot.models import AnalysisResult
from marketpilot.backtest import BacktestEngine
from marketpilot.backtest import EquityCalculator
from marketpilot.data import MARKET_UNIVERSE

class Application:

    def __init__(self):

        self.logger = setup_logger()
        self.backtester = BacktestEngine()

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

        calculator = EquityCalculator()

        backtest.equity_curve = (

            calculator.calculate(

                backtest,

                market,

            )

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

        signals = SignalEngine(market)



        defensive = self.selector.select(
            market,
        )

        result = self.strategy.evaluate(
            PortfolioState.TQQQ,
            signals,
        )

        analysis = AnalysisResult(
            market=market,
            signals=signals,
            strategy=result,
            defensive=defensive,
            backtest=backtest,
        )

        self.report.display(
            analysis,
        )

        logger.info(
            "Trades Executed : %d",
            backtest.total_trades,
        )

        if backtest.trades:

            trade = backtest.trades[-1]

            logger.info("")
            logger.info("Last Trade")
            logger.info("------------------------------")

            logger.info(
                "Date : %s",
                trade.date.date(),
            )

            logger.info(
                "From : %s",
                trade.from_state.name,
            )

            logger.info(
                "To   : %s",
                trade.to_state.name,
            )

            logger.info(
                "Reason : %s",
                ", ".join(trade.reason),
            )