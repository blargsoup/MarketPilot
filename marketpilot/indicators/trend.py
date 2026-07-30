"""
Trend indicators.
"""


class TrendIndicators:

    def __init__(
        self,
        market,
        profile,
    ):

        self.market = market
        self.profile = profile

    @property
    def signal_history(self):

        return self.market[
            self.profile.signal_asset
        ]

    @property
    def distance_from_200sma(self):

        history = self.signal_history.data

        close = history["Close"].iloc[-1]

        sma = history["SMA200"].iloc[-1]

        return (close / sma) - 1