"""
CSV report for aggregate transition analytics.
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

        for aggregate in aggregates:

            rows.append(
                {
                    "Strategy":
                        aggregate.strategy,

                    "Period":
                        aggregate.period,

                    "State Transitions":
                        aggregate.state_transitions,

                    "Trades":
                        aggregate.trades,

                    "Whipsaws":
                        aggregate.whipsaws,

                    "Whipsaw Rate":
                        aggregate.whipsaw_rate,

                    "Average Exit Timing":
                        aggregate.average_exit_timing,

                    "Median Exit Timing":
                        aggregate.median_exit_timing,

                    "Average Re-entry Timing":
                        aggregate.average_reentry_timing,

                    "Median Re-entry Timing":
                        aggregate.median_reentry_timing,

                    "Average Defensive Duration":
                        aggregate.average_defensive_duration,

                    "Median Defensive Duration":
                        aggregate.median_defensive_duration,

                    "Average Missed Upside":
                        aggregate.average_missed_upside,

                    "Median Missed Upside":
                        aggregate.median_missed_upside,

                    "Average Avoided Downside":
                        aggregate.average_avoided_downside,

                    "Median Avoided Downside":
                        aggregate.median_avoided_downside,

                    "Average Transition Quality":
                        aggregate.average_transition_quality,
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

    def generate_detailed(
        self,
        transitions_by_strategy,
        filename="transition_analytics_detailed.csv",
    ):
        """
        Write the actual state and portfolio transitions.

        transitions_by_strategy should be:

            [
                (
                    strategy_name,
                    transitions,
                    profile,
                ),
                ...
            ]
        """

        rows = []

        from marketpilot.reports.transition_analytics import (
            TransitionAnalytics,
        )

        analyzer = TransitionAnalytics()

        for (
            strategy_name,
            transitions,
            profile,
        ) in transitions_by_strategy:

            for transition in transitions:

                from_asset = (
                    analyzer._asset_for_state(
                        transition.from_state,
                        profile,
                    )
                )

                to_asset = (
                    analyzer._asset_for_state(
                        transition.to_state,
                        profile,
                    )
                )

                trade = (
                    from_asset != to_asset
                )

                rows.append(
                    {
                        "Strategy":
                            strategy_name,

                        "Date":
                            transition.date,

                        "From State":
                            transition.from_state,

                        "To State":
                            transition.to_state,

                        "From Asset":
                            from_asset,

                        "To Asset":
                            to_asset,

                        "Trade":
                            trade,

                        "Whipsaw":
                            (
                                transition.whipsaw
                                if trade
                                else False
                            ),

                        "Duration Days":
                            transition.duration_days,

                        "Exit Timing":
                            (
                                transition.exit_vs_previous_10d_high
                                if (
                                    trade
                                    and
                                    str(
                                        transition.to_state
                                    ).upper()
                                    == "DEFENSIVE"
                                )
                                else None
                            ),

                        "Re-entry Timing":
                            (
                                transition.entry_vs_10d_low
                                if (
                                    trade
                                    and
                                    str(
                                        transition.from_state
                                    ).upper()
                                    == "DEFENSIVE"
                                )
                                else None
                            ),

                        "Downside Avoided":
                            (
                                transition.downside_avoided
                                if (
                                    trade
                                    and
                                    str(
                                        transition.to_state
                                    ).upper()
                                    == "DEFENSIVE"
                                )
                                else None
                            ),

                        "Transition Quality":
                            (
                                transition.transition_quality
                                if trade
                                else None
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

        frame.to_csv(
            path,
            index=False,
        )

        return path