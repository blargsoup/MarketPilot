"""
Calculates drawdown statistics.
"""

from dataclasses import dataclass


@dataclass
class DrawdownStatistics:

    maximum_drawdown: float

    current_drawdown: float


class DrawdownAnalyzer:

    def analyze(
        self,
        equity_curve,
    ) -> DrawdownStatistics:

        peak = equity_curve[0].equity

        worst = 0.0

        current = 0.0

        for point in equity_curve:

            peak = max(
                peak,
                point.equity,
            )

            drawdown = (
                point.equity
                / peak
            ) - 1

            current = drawdown

            worst = min(
                worst,
                drawdown,
            )

        return DrawdownStatistics(

            maximum_drawdown=worst,

            current_drawdown=current,

        )