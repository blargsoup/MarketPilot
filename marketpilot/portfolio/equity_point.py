"""
Represents one point on the portfolio
equity curve.
"""

from dataclasses import dataclass

from marketpilot.strategies import (
    PortfolioState,
)


@dataclass
class EquityPoint:

    date: object

    equity: float

    state: PortfolioState