"""
MarketPilot Indicator Engine

The IndicatorEngine is the single source of truth for every calculated
market indicator.

Strategies, SignalEngine, reports, optimizers and future GUI components
should obtain indicator values from here rather than calculating them
independently.

Only raw OHLCV data is required.

Everything else is calculated on demand and cached for the lifetime of
this IndicatorEngine instance.
"""

from .moving_average import simple_moving_average
from .relative_volume import relative_volume
from .realized_volatility import realized_volatility
from .volatility_ratio import volatility_ratio
from .credit_stress import credit_stress
from .donchian import donchian_low


class IndicatorEngine:
    """
    Calculates and caches indicators for one historical market snapshot.

    One IndicatorEngine exists for one MarketView.

    Example

        indicators = IndicatorEngine(market, profile)

        indicators.rvol
        indicators.volatility_ratio
        indicators.distance_from_200sma
        indicators.credit_stress
        indicators.donchian_break
    """

    ####################################################################
    # Construction
    ####################################################################

    def __init__(
        self,
        market,
        profile,
    ):

        self.market = market
        self.profile = profile

        self._cache = {}

    ####################################################################
    # Convenience
    ####################################################################

    @property
    def signal_history(self):

        return self.market[
            self.profile.signal_asset
        ]

    ####################################################################
    # Relative Volume
    ####################################################################

    @property
    def relative_volume(self):

        if "relative_volume" not in self._cache:

            volume = self.signal_history.volume

            value = relative_volume(
                volume,
            ).iloc[-1]

            self._cache["relative_volume"] = float(value)

        return self._cache["relative_volume"]


    #
    # Temporary compatibility alias.
    #
    # Remove after all code uses relative_volume.
    #

    @property
    def realized_volatility(self):

        if "realized_volatility" not in self._cache:

            close = self.signal_history.close

            value = realized_volatility(
                close,
                window=15,
            ).iloc[-1]

            self._cache["realized_volatility"] = float(value)

        return self._cache["realized_volatility"]


    ####################################################################
    # Volatility Ratio
    ####################################################################

    @property
    def volatility_ratio(self):

        if "volatility_ratio" not in self._cache:

            close = self.signal_history.close

            value = volatility_ratio(
                close,
            ).iloc[-1]

            self._cache["volatility_ratio"] = float(value)

        return self._cache["volatility_ratio"]

        ####################################################################
        # Trend
        ####################################################################

    @property
    def sma200(self):

        if "sma200" not in self._cache:

            close = self.signal_history.close

            value = simple_moving_average(

                close,

                200,

            ).iloc[-1]

            self._cache["sma200"] = float(value)

        return self._cache["sma200"]

    @property
    def signal_price(self):

        return self.signal_history.latest_close

    @property
    def distance_from_200sma(self):

        if "distance200" not in self._cache:

            self._cache["distance200"] = (

                self.signal_price

                / self.sma200

            ) - 1

        return self._cache["distance200"]

    ####################################################################
    # Credit
    ####################################################################

    @property
    def credit_stress(self) -> float | None:

        if "credit" not in self._cache:

            #
            # Credit stress is optional.
            #
            # If HYG or LQD is unavailable at this point in history,
            # credit stress simply does not participate in the strategy.
            #

            if (
                "HYG" not in self.market.keys()
                or "LQD" not in self.market.keys()
            ):

                self._cache["credit"] = None

            else:

                hyg = self.market["HYG"].close
                lqd = self.market["LQD"].close

                #
                # We need enough overlapping observations to calculate
                # the credit-stress indicator.
                #

                if hyg.empty or lqd.empty:

                    self._cache["credit"] = None

                else:

                    value = credit_stress(
                        hyg,
                        lqd,
                    ).iloc[-1]

                    try:

                        value = float(value)

                    except (
                        TypeError,
                        ValueError,
                    ):

                        value = None

                    self._cache["credit"] = value

        return self._cache["credit"]

    ####################################################################
    # Breakout
    ####################################################################

    @property
    def donchian_break(self):

        if "donchian" not in self._cache:

            close = self.signal_history.close

            value = donchian_low(
                close,
                40,
            ).iloc[-1]

            self._cache["donchian"] = bool(value)

        return self._cache["donchian"]

    ####################################################################
    # Momentum
    ####################################################################

    def momentum_30(
        self,
        symbol: str,
    ) -> float | None:

        key = f"mom30:{symbol}"

        if key not in self._cache:

            close = self.market[symbol].close

            if len(close) < 31:
                self._cache[key] = None
            else:
                self._cache[key] = (
                    close.iloc[-1]
                    / close.iloc[-31]
                ) - 1

        return self._cache[key]

    def momentum_90(
        self,
        symbol: str,
    ) -> float | None:

        key = f"mom90:{symbol}"

        if key not in self._cache:

            close = self.market[symbol].close

            if len(close) < 91:
                self._cache[key] = None
            else:
                self._cache[key] = (
                    close.iloc[-1]
                    / close.iloc[-91]
                ) - 1

        return self._cache[key]

     ####################################################################
    # Distance Above SMA
    ####################################################################

    def distance_from_sma(
        self,
        symbol: str,
        period: int = 50,
    ) -> float:

        key = f"sma_distance:{symbol}:{period}"

        if key not in self._cache:

            history = self.market[symbol]

            close = history.close.iloc[-1]

            sma = simple_moving_average(
                history.close,
                period,
            ).iloc[-1]

            distance = (close / sma) - 1

            self._cache[key] = distance

        return self._cache[key]