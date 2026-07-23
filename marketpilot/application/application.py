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

class Application:

    def __init__(self):

        self.logger = setup_logger()

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
            "QQQ",
            "SPY",
            "HYG",
            "LQD",
            "TLT",
            "GLD",
            "XLU",
            "XLE",
        ]

        market = self.data.get_histories(symbols)

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
        )

        self.report.display(
            analysis,
        )