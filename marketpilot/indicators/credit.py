"""
Credit market indicators.
"""


class CreditIndicators:

    def __init__(
        self,
        market,
        profile,
    ):

        self.market = market

    @property
    def spread_20(self):

        hyg = self.market["HYG"].data

        lqd = self.market["LQD"].data

        ratio = (
            hyg["Close"]
            / lqd["Close"]
        )

        return float(

            ratio.pct_change(20).iloc[-1]

        )