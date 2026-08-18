"""
Checkpoint report generation.

CheckpointAnalytics performs all calculations.
This class handles CSV output and presentation formatting.
"""

from pathlib import Path

import pandas as pd

from marketpilot.reports.checkpoint_analytics import (
    CheckpointAnalytics,
)


class CheckpointReport:

    def __init__(
        self,
        output_path="output/checkpoints.csv",
        detailed_output_path="output/checkpoints_detailed.csv",
    ):

        self.output_path = Path(output_path)

        self.detailed_output_path = Path(
            detailed_output_path
        )

        self.analytics = CheckpointAnalytics()

    def generate(
        self,
        comparisons,
    ):
        """
        Generate both checkpoint CSV files.

        Returns:
            tuple[Path, Path]
        """

        detailed = self.analytics.analyze(
            comparisons
        )

        if detailed.empty:

            return (
                self.output_path,
                self.detailed_output_path,
            )

        #
        # Make sure output directory exists.
        #

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.detailed_output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        #
        # Detailed machine-readable dataset.
        #
        # Keep numeric values numeric so this file can
        # eventually feed the optimizer and UI.
        #

        detailed_output = self._build_detailed(
            detailed
        )

        detailed_output.to_csv(
            self.detailed_output_path,
            index=False,
        )

        #
        # Compact human-readable dataset.
        #

        compact = self._build_compact(
            detailed
        )

        compact.to_csv(
            self.output_path,
            index=False,
        )

        return (
            self.output_path,
            self.detailed_output_path,
        )

    # ------------------------------------------------------------------
    # Formatting helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_percent(
        value,
    ):

        if pd.isna(value):
            return ""

        return f"{value * 100:.2f}%"

    @staticmethod
    def _format_equity(
        value,
    ):

        if pd.isna(value):
            return ""

        return f"${value:,.2f}"

    @staticmethod
    def _format_date(
        value,
    ):

        if pd.isna(value):
            return ""

        return pd.Timestamp(
            value
        ).strftime("%Y-%m-%d")

    # ------------------------------------------------------------------
    # Compact report
    # ------------------------------------------------------------------

    def _build_compact(
        self,
        detailed,
    ):

        columns = [

            "Date",
            "Actual Trading Date",
            "Event",
            "Strategy",
            "State",
            "Asset",
            "Equity",
            "Checkpoint Return",
            "Drawdown From Peak",
            "Period Peak Equity",
            "Max Period Drawdown",

            "Days Aggressive",
            "Days Moderate",
            "Days Defensive",

            "State Changes",
            "Days Underwater",
            "Recovery Days",
            "Recovery Date",

            "RVol",
            "VR",
            "SPY vs 200 SMA",
            "Credit",

            "RVol > QLD",
            "VR > QLD",
            "SPY Breakdown",
            "Credit Crisis",
            "Donchian Break",
            "Donchian Confirmed",

            "State Changed",
            "Transition Reasons",
        ]

        #
        # Only select columns that actually exist.
        #
        # This makes the report tolerant of analytics
        # additions/removals.
        #

        columns = [
            column
            for column in columns
            if column in detailed.columns
        ]

        compact = detailed[
            columns
        ].copy()

        #
        # Percent fields
        #

        percent_columns = [

            "Checkpoint Return",
            "Drawdown From Peak",
            "Max Period Drawdown",
            "RVol",
            "SPY vs 200 SMA",
            "Credit",
        ]

        for column in percent_columns:

            if column in compact.columns:

                compact[column] = (
                    compact[column]
                    .apply(
                        self._format_percent
                    )
                )

        #
        # VR
        #

        if "VR" in compact.columns:

            compact["VR"] = (
                compact["VR"]
                .apply(
                    lambda value:
                    ""
                    if pd.isna(value)
                    else f"{value:.2f}"
                )
            )

        #
        # Equity
        #

        if "Equity" in compact.columns:

            compact["Equity"] = (
                compact["Equity"]
                .apply(
                    self._format_equity
                )
            )

        #
        # Period peak equity
        #

        if "Period Peak Equity" in compact.columns:

            compact["Period Peak Equity"] = (
                compact["Period Peak Equity"]
                .apply(
                    self._format_equity
                )
            )

        #
        # Dates
        #

        for column in (
            "Date",
            "Actual Trading Date",
            "Recovery Date",
        ):

            if column in compact.columns:

                compact[column] = (
                    compact[column]
                    .apply(
                        self._format_date
                    )
                )

        return compact

    # ------------------------------------------------------------------
    # Detailed report
    # ------------------------------------------------------------------

    @staticmethod
    def _build_detailed(
        detailed,
    ):

        result = detailed.copy()

        #
        # Keep numeric values numeric.
        #
        # The detailed CSV is intended for:
        #
        # - Python
        # - spreadsheets
        # - plotting
        # - future UI
        # - optimizer
        #

        for column in (
            "Date",
            "Actual Trading Date",
            "Recovery Date",
        ):

            if column not in result.columns:
                continue

            result[column] = (
                pd.to_datetime(
                    result[column],
                    errors="coerce",
                )
                .dt.strftime(
                    "%Y-%m-%d"
                )
            )

        return result