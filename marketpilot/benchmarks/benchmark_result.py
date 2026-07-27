"""
Result of a benchmark buy-and-hold simulation.
"""

from dataclasses import dataclass


@dataclass
class BenchmarkResult:

    symbol: str

    starting_value: float

    ending_value: float

    total_return: float

    annual_return: float

    max_drawdown: float