"""
Calculates overall portfolio performance.
"""

from marketpilot.statistics.metrics import (
    BacktestStatistics,
)

from .drawdown import calculate_drawdown
from .trade_analyzer import (
    TradeAnalyzer,
    TradeStatistics,
)


class PerformanceAnalyzer:

    def analyze(
        self,
        backtest,
    ) -> BacktestStatistics:

        curve = backtest.equity_curve

        if not curve:
            return BacktestStatistics()

        #
        # Portfolio Returns
        #

        start = curve[0].equity
        end = curve[-1].equity

        total_return = (
            end / start
        ) - 1

        years = len(curve) / 252

        annual_return = (
            (end / start)
            ** (1 / years)
        ) - 1

        #
        # Drawdown
        #

        drawdown = calculate_drawdown(
            curve
        )

        #
        # Trade Performance
        #

        completed_trades = TradeAnalyzer().analyze(
            backtest
        )

        backtest.completed_trades = completed_trades

        trade_stats = TradeStatistics()

        if completed_trades:

            returns = [
                trade.return_pct
                for trade in completed_trades
            ]

            trade_stats.trades = len(returns)

            trade_stats.win_rate = (
                sum(r > 0 for r in returns)
                / len(returns)
            )

            trade_stats.average_trade = (
                sum(returns)
                / len(returns)
            )

            trade_stats.best_trade = max(
                returns
            )

            trade_stats.worst_trade = min(
                returns
            )

        #
        # Final Statistics
        #

        stats = BacktestStatistics(

            starting_value=start,

            ending_value=end,

            total_return=total_return,

            annual_return=annual_return,

            max_drawdown=drawdown.max_drawdown,

            trades=trade_stats.trades,

            win_rate=trade_stats.win_rate,

            average_trade=trade_stats.average_trade,

            best_trade=trade_stats.best_trade,

            worst_trade=trade_stats.worst_trade,

        )

        backtest.performance = stats

        backtest.trade_statistics = trade_stats

        return stats