"""
Result of a completed backtest.

This object is the central container returned by the BacktestEngine.

It contains:

    • Every daily simulation
    • Every trade executed
    • The portfolio equity curve
    • The trading calendar
    • Benchmark results
    • Trade statistics

Additional analysis (performance, statistics, charts, etc.) is
attached later without requiring the engine to know about it.
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

    calendar = None

    ####################################################################
    # Analysis Results
    ####################################################################

    benchmarks: list = field(default_factory=list)

    trade_statistics = None

    ####################################################################
    # Convenience Properties
    ####################################################################

    @property
    def total_days(self):

        return len(self.simulations)

    @property
    def total_trades(self):

        return len(self.trades)

    @property
    def first_day(self):

        if not self.simulations:
            return None

        return self.simulations[0]

    @property
    def last_day(self):

        if not self.simulations:
            return None

        return self.simulations[-1]

    ####################################################################
    # Portfolio Helpers
    ####################################################################

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