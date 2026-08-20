"""
CSV output for aggregate transition analytics.
"""

from pathlib import Path

import pandas as pd


class TransitionAnalyticsReport:

    def __init__(
        self,
        output_dir="output",
    ):

        self.output_dir = Path(
            output_dir
        )

    def generate(
        self,
        aggregates,
        filename="transition_analytics.csv",
    ):

        rows = []

        for a in aggregates:

            rows.append(
                {
                    "Strategy": a.strategy,
                    "Period": a.period,

                    "Transitions": (
                        a.transitions
                    ),

                    "Whipsaws": (
                        a.whipsaws
                    ),

                    "Whipsaw Rate": (
                        a.whipsaw_rate
                    ),

                    "Average Exit Timing": (
                        a.average_exit_timing
                    ),

                    "Median Exit Timing": (
                        a.median_exit_timing
                    ),

                    "Average Re-entry Timing": (
                        a.average_reentry_timing
                    ),

                    "Median Re-entry Timing": (
                        a.median_reentry_timing
                    ),

                    "Average Defensive Duration": (
                        a.average_defensive_duration
                    ),

                    "Median Defensive Duration": (
                        a.median_defensive_duration
                    ),

                    "Average Missed Upside": (
                        a.average_missed_upside
                    ),

                    "Median Missed Upside": (
                        a.median_missed_upside
                    ),

                    "Average Avoided Downside": (
                        a.average_avoided_downside
                    ),

                    "Median Avoided Downside": (
                        a.median_avoided_downside
                    ),

                    "Average Transition Quality": (
                        a.average_transition_quality
                    ),
                }
            )

        frame = pd.DataFrame(
            rows
        )

        path = (
            self.output_dir
            / filename
        )

        path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        frame.to_csv(
            path,
            index=False,
        )

        return path