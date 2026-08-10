"""
Result from one simulated day.
"""

from dataclasses import dataclass


@dataclass
class SimulationResult:

    #
    # Backtest context
    #

    context: object

    #
    # Market information
    #

    market: object

    #
    # Indicator / signal snapshot
    #

    signals: object

    #
    # Strategy decision
    #

    strategy: object

    #
    # Portfolio state AFTER today's evaluation
    #

    portfolio_state: object

    #
    # Current symbol being held
    #

    symbol: str

    #
    # Portfolio equity
    #

    equity: float