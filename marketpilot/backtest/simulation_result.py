"""
Result from one simulated day.
"""

from dataclasses import dataclass


@dataclass
class SimulationResult:

    context: object

    market: dict

    signals: object

    strategy: object