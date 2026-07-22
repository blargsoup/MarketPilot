"""
Calculates all strategy signals.
"""

from marketpilot.indicators import (
    realized_volatility,
    volatility_ratio,
    simple_moving_average,
)


class SignalEngine:

    def __init__(self, market):

        self.market = market

        self.qqq = market["QQQ"]
        self.spy = market["SPY"]

        self._calculate()

    def _calculate(self):

        self.rvol_series = realized_volatility(
            self.qqq.close
        )

        self.vr_series = volatility_ratio(
            self.qqq.close
        )

        self.spy_sma200 = simple_moving_average(
            self.spy.close,
            200,
        )

        self.rvol = float(
            self.rvol_series.iloc[-1]
        )

        self.vr = float(
            self.vr_series.iloc[-1]
        )

        self.spy_distance = (
            (
                self.spy.latest_close
                - self.spy_sma200.iloc[-1]
            )
            / self.spy_sma200.iloc[-1]
        ) * 100