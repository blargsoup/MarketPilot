"""
Relative volatility indicators.
"""


class VolatilityIndicators:

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
    def rvol_21(self):

        history = self.signal_history.data

        return float(
            history["RVol21"].iloc[-1]
        )

    @property
    def volume_ratio(self):

        history = self.signal_history.data

        return float(
            history["VR"].iloc[-1]
        )