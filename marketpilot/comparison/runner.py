"""Run multiple strategies over one market history."""

from dataclasses import dataclass

from marketpilot.performance import PerformanceAnalyzer


@dataclass
class StrategyComparison:
    """A completed strategy backtest and its performance summary."""

    name: str
    backtest: object
    statistics: object


class StrategyComparisonRunner:
    """Runs strategies through the same backtest and analysis pipeline."""

    def __init__(self, backtester):
        self._backtester = backtester
        self._analyzer = PerformanceAnalyzer()

    def run(self, market, strategies) -> list[StrategyComparison]:
        """Return comparable results for every supplied strategy."""

        comparisons = []

        for strategy in strategies:
            backtest = self._backtester.run(market, strategy)
            statistics = self._analyzer.analyze(backtest)
            comparisons.append(
                StrategyComparison(
                    name=strategy.name,
                    backtest=backtest,
                    statistics=statistics,
                )
            )

        return comparisons
