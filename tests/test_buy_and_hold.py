"""
Validation tests for Buy & Hold strategies.
"""

from marketpilot.backtest import BacktestEngine
from marketpilot.data import MarketDataService
from marketpilot.strategies import (
    BuyAndHoldStrategy,
    PortfolioState,
)
from marketpilot.data import MARKET_UNIVERSE


def run():

    print("Running Buy & Hold tests...")

    market = MarketDataService().get_histories(
        [asset.symbol for asset in MARKET_UNIVERSE]
    )

    engine = BacktestEngine()

    result = engine.run(
        market,
        BuyAndHoldStrategy(
            PortfolioState.TQQQ
        ),
    )

    assert result.total_trades == 0

    assert len(result.equity_curve) > 100

    assert (
        result.equity_curve[-1].equity
        > result.equity_curve[0].equity
    )

    print("PASS")


if __name__ == "__main__":
    run()