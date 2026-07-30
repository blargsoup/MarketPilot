"""
Portfolio allocation states.
"""

from enum import Enum


class PortfolioState(Enum):

    AGGRESSIVE = "Aggressive"

    MODERATE = "Moderate"

    DEFENSIVE = "Defensive"