from dataclasses import dataclass


@dataclass
class BacktestStatistics:

    starting_value: float
    ending_value: float

    total_return: float
    annual_return: float

    max_drawdown: float

    trades: int

    win_rate: float

    average_trade: float

    best_trade: float

    worst_trade: float