"""
Central indicator engine.

The engine exposes indicator families through a single
interface while caching calculated values.
"""

from .volatility import VolatilityIndicators
from .trend import TrendIndicators
from .credit import CreditIndicators
from .breakout import BreakoutIndicators


class IndicatorEngine:

    def __init__(
        self,
        market,
        profile,
    ):

        self.market = market
        self.profile = profile

        #
        # Individual indicator families.
        #

        self.volatility = VolatilityIndicators(
            market,
            profile,
        )

        self.trend = TrendIndicators(
            market,
            profile,
        )

        self.credit = CreditIndicators(
            market,
            profile,
        )

        self.breakout = BreakoutIndicators(
            market,
            profile,
        )