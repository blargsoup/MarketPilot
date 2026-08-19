"""
CSV report for transition timing analytics.
"""

from pathlib import Path

import pandas as pd


class TransitionTimingReport:

    def __init__(
        self,
        output_path="output/transition_timing.csv",
    ):
        self.output_path = Path(
            output_path
        )

    def generate(
        self,
        transitions,
        filename=None,
    ):

        if filename:
            self.output_path = self.output_path.parent / filename

        rows = []

        for transition in transitions:

            rows.append(
                {
                    "Date": transition.date,
                    "Exit Date": transition.exit_date,

                    "From State": (
                        transition.from_state
                    ),

                    "To State": (
                        transition.to_state
                    ),

                    "Exited Asset": (
                        transition.exited_asset
                    ),

                    "Entered Asset": (
                        transition.entered_asset
                    ),

                    "Duration Days": (
                        transition.duration_days
                    ),

                    "Whipsaw": (
                        transition.whipsaw
                    ),

                    "Entry Price": (
                        transition.entry_price
                    ),

                    "Exit Price": (
                        transition.exit_price
                    ),

                    "Previous 10D High": (
                        transition.previous_10d_high
                    ),

                    "Following 10D Low": (
                        transition.following_10d_low
                    ),

                    "Entry vs 10D Low": (
                        transition.entry_vs_10d_low
                    ),

                    "Exit vs Previous 10D High": (
                        transition.exit_vs_previous_10d_high
                    ),

                    "Return 1D": (
                        transition.return_1d
                    ),

                    "Return 3D": (
                        transition.return_3d
                    ),

                    "Return 5D": (
                        transition.return_5d
                    ),

                    "Return 10D": (
                        transition.return_10d
                    ),

                    "Return 20D": (
                        transition.return_20d
                    ),

                    "MAE": (
                        transition.mae
                    ),

                    "MFE": (
                        transition.mfe
                    ),

                    "Downside Avoided": (
                        transition.downside_avoided
                    ),

                    "Upside Captured": (
                        transition.upside_captured
                    ),

                    "Timing Score": (
                        transition.timing_score
                    ),

                    "Outcome Score": (
                        transition.outcome_score
                    ),

                    "Transition Quality": (
                        transition.transition_quality
                    ),

                    "Timing Class": (
                        transition.timing_class
                    ),
                }
            )

        frame = pd.DataFrame(
            rows
        )

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        frame.to_csv(
            self.output_path,
            index=False,
        )

        return self.output_path

    def generate_summary(
        self,
        summaries,
        output_path="output/transition_timing_summary.csv",
    ):

        frame = pd.DataFrame(
            [
                {
                    "Category": s.category,

                    "Transitions": s.transitions,

                    "Avg Timing Score": s.average_timing_score,
                    "Median Timing Score": s.median_timing_score,

                    "Avg Price Gap": s.average_price_gap,
                    "Median Price Gap": s.median_price_gap,

                    "Avg Outcome Score": s.average_outcome_score,

                    "Avg 10D Return": s.average_10d_return,

                    "Avg Downside Avoided": s.average_downside_avoided,

                    "Avg Duration": s.average_duration,

                    "Whipsaw Rate": s.whipsaw_rate,

                    "Excellent": s.excellent,
                    "Good": s.good,
                    "Fair": s.fair,
                    "Poor": s.poor,
                    "Very Poor": s.very_poor,
                }
                for s in summaries
            ]
        )

        frame.to_csv(
            output_path,
            index=False,
        )

        return output_path