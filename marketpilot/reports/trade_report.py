"""
Trade Report

Exports all trades to a CSV file.
"""

from pathlib import Path

import pandas as pd


class TradeReport:

    def display(self, logger, backtest):

        output = Path("output")

        output.mkdir(exist_ok=True)

        #
        # Build equity lookup
        #

        equity_lookup = {
            point.date: point.equity
            for point in backtest.equity_curve
        }

        rows = []

        for trade in backtest.trades:

            rows.append(
                {
                    "Date": trade.date.strftime("%Y-%m-%d"),
                    "From State": trade.from_state.name,
                    "To State": trade.to_state.name,
                    "From Asset": trade.from_symbol,
                    "To Asset": trade.to_symbol,
                    "Equity": equity_lookup.get(trade.date, 0.0),
                    "Reasons": ", ".join(trade.reason)
                    if trade.reason
                    else "",
                }
            )

        df = pd.DataFrame(rows)

        filename = output / "trades.csv"

        df.to_csv(filename, index=False)

        logger.info("")
        logger.info("=" * 70)
        logger.info("TRADE HISTORY")
        logger.info("=" * 70)
        logger.info("CSV exported to:")
        logger.info("    %s", filename)
        logger.info("Trades : %d", len(df))
        logger.info("")