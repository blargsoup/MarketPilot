"""
Represents the current state of a backtest.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class BacktestContext:

    current_date: datetime

    current_index: int

    total_days: int