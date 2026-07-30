"""
Breakout indicators.
"""


class BreakoutIndicators:

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
    def donchian_break(self):

        history = self.signal_history.data

        high20 = history["High"].rolling(20).max()

        return bool(

            history["Close"].iloc[-1]
            < high20.iloc[-2]

        )