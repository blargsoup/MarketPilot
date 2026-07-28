"""
General strategy validation.
"""

from marketpilot.backtest import BacktestEngine
from marketpilot.data import (
    MarketDataService,
    MARKET_UNIVERSE,
)
from marketpilot.strategies import ARVolStrategy


def run():

    print("Running ARVol tests...")

    market = MarketDataService().get_histories(
        [
            asset.symbol
            for asset in MARKET_UNIVERSE
        ]
    )

    result = BacktestEngine().run(
        market,
        ARVolStrategy(),
    )

    assert result.total_days > 1000
    assert len(result.trades) > 0
    assert len(result.equity_curve) == result.total_days

    print("PASS")


if __name__ == "__main__":
    run()