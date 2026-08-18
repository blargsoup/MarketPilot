"""
Checkpoint report generation.

CheckpointAnalytics performs the calculations.
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
    ):
        self.output_path = Path(output_path)

    def generate(
        self,
        market,
        strategy_comparisons,
    ):
        analytics = CheckpointAnalytics()

        report = analytics.analyze(
            market=market,
            strategy_comparisons=strategy_comparisons,
        )

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        report.to_csv(
            self.output_path,
            index=False,
        )

        return self.output_path

    # ------------------------------------------------------------------
    # Formatting
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
            "Max Period Drawdown",
            "Days Aggressive",
            "Days Moderate",
            "Days Defensive",
            "State Changes",
            "Days Underwater",
            "Recovery Days",
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

        compact = detailed[
            columns
        ].copy()

        #
        # Human-readable CSV formatting.
        #

        for column in (
            "Checkpoint Return",
            "Drawdown From Peak",
            "Max Period Drawdown",
            "RVol",
            "SPY vs 200 SMA",
            "Credit",
        ):

            compact[column] = (
                compact[column]
                .apply(
                    self._format_percent
                )
            )

        compact["VR"] = (
            compact["VR"]
            .apply(
                lambda value:
                    ""
                    if pd.isna(value)
                    else f"{value:.2f}"
            )
        )

        compact["Equity"] = (
            compact["Equity"]
            .apply(
                self._format_equity
            )
        )

        compact["Date"] = (
            compact["Date"]
            .apply(
                self._format_date
            )
        )

        compact[
            "Actual Trading Date"
        ] = (
            compact[
                "Actual Trading Date"
            ]
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
        # This is intentional: the detailed CSV is meant
        # for Python, spreadsheets, plotting, and eventually
        # the optimizer/UI.
        #

        result["Date"] = pd.to_datetime(
            result["Date"]
        ).dt.strftime(
            "%Y-%m-%d"
        )

        result[
            "Actual Trading Date"
        ] = pd.to_datetime(
            result[
                "Actual Trading Date"
            ]
        ).dt.strftime(
            "%Y-%m-%d"
        )

        if "Recovery Date" in result:

            result[
                "Recovery Date"
            ] = pd.to_datetime(
                result[
                    "Recovery Date"
                ],
                errors="coerce",
            ).dt.strftime(
                "%Y-%m-%d"
            )

        return result

    # ------------------------------------------------------------------
    # Generate
    # ------------------------------------------------------------------

    def generate(
        self,
        comparisons,
    ):
        """
        Generate both checkpoint CSVs.

        Returns:
            tuple[Path, Path]
        """

        detailed = (
            self.analytics.analyze(
                comparisons
            )
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

        detailed_output = (
            self._build_detailed(
                detailed
            )
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