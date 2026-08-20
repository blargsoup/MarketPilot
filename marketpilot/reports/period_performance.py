"""
Performance analysis across historical periods.
"""

from dataclasses import dataclass

import pandas as pd

from .analysis_periods import ANALYSIS_PERIODS


@dataclass
class PeriodPerformance:
    strategy: str
    period: str

    start_date: object
    end_date: object

    starting_equity: float | None
    ending_equity: float | None

    total_return: float | None
    cagr: float | None
    max_drawdown: float | None

    trades: int | None


class PeriodPerformanceAnalyzer:

    def analyze(
        self,
        comparison,
    ):

        simulations = (
            comparison.backtest.simulations
        )

        if not simulations:
            return []

        rows = []

        for simulation in simulations:

            rows.append(
                {
                    "date":
                        pd.Timestamp(
                            simulation.context.current_date
                        ),

                    "equity":
                        float(
                            simulation.equity
                        ),
                }
            )

        frame = pd.DataFrame(
            rows
        ).sort_values(
            "date"
        )

        results = []

        for period_name, definition in ANALYSIS_PERIODS.items():

            period = self._filter(
                frame,
                definition["start"],
                definition["end"],
            )

            results.append(
                self._calculate(
                    period,
                    comparison.name,
                    period_name,
                    comparison,
                )
            )

        return results

    def _filter(
        self,
        frame,
        start,
        end,
    ):

        result = frame[
            frame["date"]
            >= pd.Timestamp(start)
        ]

        if end is not None:

            result = result[
                result["date"]
                < pd.Timestamp(end)
            ]

        return result

    def _calculate(
        self,
        frame,
        strategy,
        period,
        comparison,
    ):

        if frame.empty:

            return PeriodPerformance(
                strategy,
                period,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
                None,
            )

        starting_equity = float(
            frame.iloc[0]["equity"]
        )

        ending_equity = float(
            frame.iloc[-1]["equity"]
        )

        total_return = (
            ending_equity
            / starting_equity
            - 1.0
        )

        days = (
            frame.iloc[-1]["date"]
            - frame.iloc[0]["date"]
        ).days

        years = days / 365.25

        if (
            years > 0
            and starting_equity > 0
            and ending_equity > 0
        ):

            cagr = (
                ending_equity
                / starting_equity
            ) ** (
                1.0 / years
            ) - 1.0

        else:

            cagr = None

        running_max = (
            frame["equity"]
            .cummax()
        )

        drawdown = (
            frame["equity"]
            / running_max
            - 1.0
        )

        max_drawdown = float(
            drawdown.min()
        )

        return PeriodPerformance(
            strategy=strategy,
            period=period,

            start_date=frame.iloc[0]["date"],
            end_date=frame.iloc[-1]["date"],

            starting_equity=starting_equity,
            ending_equity=ending_equity,

            total_return=total_return,
            cagr=cagr,
            max_drawdown=max_drawdown,

            trades=None,
        )