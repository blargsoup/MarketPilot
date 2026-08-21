"""
Result of a completed backtest.
"""

from dataclasses import dataclass, field

from .simulation_result import SimulationResult
from .trade import Trade


@dataclass
class BacktestResult:

    ####################################################################
    # Core Backtest Data
    ####################################################################

    simulations: list[SimulationResult]

    trades: list[Trade] = field(default_factory=list)

    equity_curve: list = field(default_factory=list)

    calendar: object | None = None

    ####################################################################
    # Analysis Results
    ####################################################################

    benchmarks: list = field(default_factory=list)

    trade_statistics = None

    performance = None

    completed_trades: list = field(default_factory=list)

    ####################################################################
    # Convenience
    ####################################################################

    @property
    def total_days(self):

        return len(self.simulations)

    @property
    def total_trades(self):

        return len(self.trades)

    @property
    def first_day(self):

        return self.simulations[0] if self.simulations else None

    @property
    def last_day(self):

        return self.simulations[-1] if self.simulations else None

    @property
    def starting_equity(self):

        if not self.equity_curve:
            return 0.0

        return self.equity_curve[0].equity

    @property
    def ending_equity(self):

        if not self.equity_curve:
            return 0.0

        return self.equity_curve[-1].equity