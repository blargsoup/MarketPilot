from pathlib import Path
import pandas as pd


class TradeExporter:

    def export(self, trades):

        rows = []

        for trade in trades:

            rows.append({

                "Date": trade.date,

                "From": trade.old_state,

                "To": trade.new_state,

                "Old Asset": trade.old_asset,

                "New Asset": trade.new_asset,

                "Equity": trade.equity,

                "Reasons": "; ".join(trade.reasons),

            })

        output = Path("output")

        output.mkdir(exist_ok=True)

        pd.DataFrame(rows).to_csv(

            output / "trades.csv",

            index=False,

        )