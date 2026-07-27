"""
Result from one simulated day.
"""

from dataclasses import dataclass


@dataclass
class SimulationResult:

    context: object

    signals: object

    strategy: object
