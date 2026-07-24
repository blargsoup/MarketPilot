"""
Calculates portfolio equity through time.
"""

from dataclasses import dataclass


@dataclass
class EquityPoint:

    date: object

    equity: float

    state: object