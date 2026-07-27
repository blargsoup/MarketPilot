from marketpilot.models import MarketHistory


def slice_market(
    market,
    current_date,
):

    sliced = {}

    for symbol, history in market.items():

        df = history.data.loc[
            history.data.index <= current_date
        ]

        sliced[symbol] = MarketHistory(
            symbol=symbol,
            data=df,
        )

    return sliced