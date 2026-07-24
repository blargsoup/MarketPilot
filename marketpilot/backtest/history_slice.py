"""
Creates historical market snapshots.

Each snapshot contains only the
data that would have existed on
that trading day.
"""

from marketpilot.models import MarketHistory


def slice_market(
    market,
    index,
):

    sliced = {}

    for symbol, history in market.items():

        df = history.data.iloc[: index + 1].copy()

        sliced[symbol] = MarketHistory(
            symbol=symbol,
            data=df,
        )

    return sliced