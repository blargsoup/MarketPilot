from .metrics import BacktestStatistics


class Statistics:

    def calculate(
        self,
        backtest,
    ):

        curve = backtest.equity_curve

        start = curve[0].equity
        end = curve[-1].equity

        total_return = (
            end / start
        ) - 1

        years = (
            len(curve)
            / 252
        )

        annual_return = (
            (end / start)
            ** (1 / years)
        ) - 1

        return BacktestStatistics(

            starting_value=start,

            ending_value=end,

            total_return=total_return,

            annual_return=annual_return,

            max_drawdown=0,

            trades=len(backtest.trades),

            win_rate=0,

            average_trade=0,

            best_trade=0,

            worst_trade=0,

        )