"""
Represents one portfolio transition.
"""

from dataclasses import dataclass
from datetime import datetime

from marketpilot.strategies import PortfolioState


@dataclass
class Trade:

    date: datetime

    from_state: PortfolioState

    to_state: PortfolioState

    from_symbol: str

    to_symbol: str

    reason: list[str]