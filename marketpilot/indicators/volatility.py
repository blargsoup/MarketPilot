"""
Volatility indicators.

This module exposes the volatility-related indicators used by
MarketPilot strategies.

Current indicators:

    • Realized Volatility (annualized)
    • Volatility Ratio

The underlying calculations are implemented in the individual
indicator modules.
"""

from .realized_volatility import realized_volatility
from .volatility_ratio import volatility_ratio


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
    def realized_volatility(self):
        """
        Current annualized realized volatility.

        Returns
        -------
        float

            Example:
                0.18 = 18%
        """

        history = self.signal_history.data

        return float(

            realized_volatility(

                history["Close"]

            ).iloc[-1]

        )

    @property
    def volatility_ratio(self):
        """
        Current Volatility Ratio.

        Returns
        -------
        float
        """

        history = self.signal_history.data

        return float(

            volatility_ratio(

                history["Close"]

            ).iloc[-1]

        )