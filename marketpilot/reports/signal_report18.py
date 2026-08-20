"""
CSV reporting for signal and transition analytics.
"""

from pathlib import Path


class SignalReport:

    def __init__(
        self,
        output_dir="output",
    ):

        self.output_dir = Path(
            output_dir
        )

    def generate(
        self,
        comparisons,
    ):

        from marketpilot.reports.signal_analytics import (
            SignalAnalytics,
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        analytics = SignalAnalytics()

        (
            signal_events,
            signal_summary,
            transition_events,
        ) = analytics.analyze(
            comparisons
        )

        paths = {}

        paths["signal_events"] = (
            self.output_dir
            / "signal_events.csv"
        )

        paths["signal_summary"] = (
            self.output_dir
            / "signal_summary.csv"
        )

        paths["transition_analytics"] = (
            self.output_dir
            / "transition_analytics.csv"
        )

        signal_events.to_csv(
            paths["signal_events"],
            index=False,
        )

        signal_summary.to_csv(
            paths["signal_summary"],
            index=False,
        )

        transition_events.to_csv(
            paths["transition_analytics"],
            index=False,
        )

        return paths