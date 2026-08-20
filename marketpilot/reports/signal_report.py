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

        #
        # Collect signal events from every strategy comparison.
        #
        events = []

        for comparison in comparisons:

            backtest = getattr(
                comparison,
                "backtest",
                None,
            )

            if backtest is None:
                continue

            #
            # Signal events may be stored directly on the
            # backtest result.
            #
            comparison_events = getattr(
                backtest,
                "signal_events",
                None,
            )

            if comparison_events:

                events.extend(
                    comparison_events
                )

        #
        # Build analytics using the event collection.
        #
        analytics = SignalAnalytics(
            events
        )

        #
        # Analyze the collected events.
        #
        signal_events = analytics.analyze()

        #
        # Aggregate signal results.
        #
        signal_summary = analytics.summarize(
            signal_events
        )

        #
        # Transition analytics are derived from the
        # attribution rows.
        #
        transition_events = signal_events

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

        #
        # Write event attribution.
        #
        analytics.write_attribution(
            signal_events,
            paths["signal_events"],
        )

        #
        # Write aggregate summary.
        #
        analytics.write_summary(
            signal_summary,
            paths["signal_summary"],
        )

        #
        # Write transition analytics.
        #
        analytics.write_attribution(
            transition_events,
            paths["transition_analytics"],
        )

        return paths