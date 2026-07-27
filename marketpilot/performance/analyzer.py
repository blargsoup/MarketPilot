"""
Analyzes completed backtests.
"""

from .drawdown import calculate_drawdown
from marketpilot.statistics import Statistics


class PerformanceAnalyzer:

    def analyze(
        self,
        backtest,
    ):

        #
        # Basic statistics
        #

        stats = Statistics().calculate(
            backtest
        )

        #
        # Drawdowns
        #

        drawdown = calculate_drawdown(
            backtest.equity_curve
        )

        stats.max_drawdown = drawdown.max_drawdown

        return stats