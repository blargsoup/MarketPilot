"""
Drawdown calculations.
"""

from dataclasses import dataclass


@dataclass
class DrawdownResult:

    max_drawdown: float


def calculate_drawdown(curve):

    peak = curve[0].equity

    worst = 0

    for point in curve:

        if point.equity > peak:

            peak = point.equity

        dd = (
            point.equity / peak
        ) - 1

        if dd < worst:

            worst = dd

    return DrawdownResult(
        max_drawdown=worst,
    )