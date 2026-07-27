"""
Result of a completed backtest.
"""

from dataclasses import dataclass, field

from .simulation_result import SimulationResult
from .trade import Trade


@dataclass
class BacktestResult:

    simulations: list[SimulationResult]

    trades: list[Trade] = field(default_factory=list)

    equity_curve: list = field(default_factory=list)

    benchmarks: list = field(default_factory=list)

    @property
    def total_days(self):

        return len(self.simulations)

    @property
    def total_trades(self):

        return len(self.trades)

    @property
    def first_day(self):

        return self.simulations[0]

    @property
    def last_day(self):

        return self.simulations[-1]
