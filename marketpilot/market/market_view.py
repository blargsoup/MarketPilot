"""
A read-only view of the market at a specific point in time.

Instead of copying DataFrames every day, this class simply
limits all history to the current trading index.
"""

from marketpilot.models import MarketHistory


class MarketView:

    def __init__(
        self,
        market: dict[str, MarketHistory],
        current_date,
    ):

        self._market = market
        self._current_date = current_date

    def __getitem__(
        self,
        symbol,
    ):

        history = self._market[symbol]

        return MarketHistory(

            symbol=history.symbol,

            data=history.data.loc[: self._current_date],

        )

    def items(self):

        for symbol in self._market:

            yield symbol, self[symbol]

    def keys(self):

        return self._market.keys()

    def values(self):

        for symbol in self._market:

            yield self[symbol]
