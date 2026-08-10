"""
Analyzes completed trades.
"""

from dataclasses import dataclass


@dataclass
class TradePerformance:

    entry_date: object
    exit_date: object

    asset: str

    entry_value: float
    exit_value: float

    return_pct: float

    days_held: int


@dataclass
class TradeStatistics:

    trades: int = 0

    win_rate: float = 0.0

    average_trade: float = 0.0

    best_trade: float = 0.0

    worst_trade: float = 0.0


class TradeAnalyzer:

    def analyze(
        self,
        backtest,
    ):

        curve = backtest.equity_curve
        trades = backtest.trades

        if len(trades) < 2:
            return []

        #
        # Build a lookup so we can instantly
        # find an equity point by date.
        #

        curve_lookup = {

            point.date: point

            for point in curve

        }

        completed = []

        for i in range(len(trades) - 1):

            trade = trades[i]
            next_trade = trades[i + 1]

            entry = curve_lookup.get(
                trade.date
            )

            exit = curve_lookup.get(
                next_trade.date
            )

            #
            # Skip if something went wrong.
            #

            if entry is None or exit is None:
                continue

            completed.append(

                TradePerformance(

                    entry_date=trade.date,

                    exit_date=next_trade.date,

                    asset=trade.to_symbol,

                    entry_value=entry.equity,

                    exit_value=exit.equity,

                    return_pct=(

                        exit.equity
                        / entry.equity

                    ) - 1,

                    days_held=(

                        next_trade.date
                        - trade.date

                    ).days,

                )

            )

        return completed