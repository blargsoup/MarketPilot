"""
Rank the most significant transition timing opportunities.

This report consumes transition_analytics_detailed.csv rather than
reconstructing timing metrics from transition objects.

Sections produced:

    TOP_LATE_EXITS
    TOP_LATE_RE-ENTRIES
    TOP_WHIPSAWS

The detailed transition analytics remain the authoritative source for
all timing calculations.
"""

from pathlib import Path

import pandas as pd


class TransitionOpportunityReport:
    """Generate ranked transition timing diagnostics."""

    TOP_N = 20

    def generate(
        self,
        detailed_path="output/transition_analytics_detailed.csv",
        filename="transition_opportunities.csv",
    ):
        """
        Generate the ranked opportunity report.

        Parameters
        ----------
        detailed_path:
            Path to the authoritative detailed transition analytics CSV.

        filename:
            Filename for the resulting report under output/.
        """

        detailed_path = Path(detailed_path)

        if not detailed_path.exists():
            raise FileNotFoundError(
                "Transition analytics detail file not found: "
                f"{detailed_path}"
            )

        df = pd.read_csv(detailed_path)

        if df.empty:
            raise ValueError(
                "Transition analytics detail file is empty."
            )

        #
        # Normalize column names so minor capitalization/spacing
        # differences don't break the report.
        #

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        #
        # Required fields.
        #

        required = [
            "Strategy",
            "Trade",
            "Whipsaw",
        ]

        missing = [
            column
            for column in required
            if column not in df.columns
        ]

        if missing:
            raise ValueError(
                "transition_analytics_detailed.csv is missing "
                f"required columns: {missing}"
            )

        #
        # Make sure the timing columns exist.
        #
        # Older versions may use slightly different spellings.
        #

        exit_column = self._find_column(
            df,
            [
                "Exit Timing",
                "Exit Timing %",
                "Exit Timing Percent",
            ],
        )

        reentry_column = self._find_column(
            df,
            [
                "Re-entry Timing",
                "Reentry Timing",
                "Re-entry Timing %",
                "Reentry Timing %",
            ],
        )

        missed_upside_column = self._find_column(
            df,
            [
                "Missed Upside",
                "Missed Upside %",
            ],
        )

        downside_column = self._find_column(
            df,
            [
                "Downside Avoided",
                "Downside Avoided %",
            ],
        )

        #
        # Convert timing fields to numeric.
        #

        if exit_column:
            df[exit_column] = self._numeric(
                df[exit_column]
            )

        if reentry_column:
            df[reentry_column] = self._numeric(
                df[reentry_column]
            )

        if missed_upside_column:
            df[missed_upside_column] = self._numeric(
                df[missed_upside_column]
            )

        if downside_column:
            df[downside_column] = self._numeric(
                df[downside_column]
            )

        #
        # Normalize boolean fields.
        #

        df["Trade"] = df["Trade"].apply(
            self._to_bool
        )

        df["Whipsaw"] = df["Whipsaw"].apply(
            self._to_bool
        )

        sections = []

        #
        # ============================================================
        # TOP 20 LATE EXITS
        # ============================================================
        #
        # A late exit has a negative Exit Timing value.
        #
        # Example:
        #
        #     -25% = we exited 25% below the previous 10-day high.
        #
        # More negative = worse.
        #
        # Only actual portfolio trades are included.
        #

        if exit_column:

            late_exits = df[
                df["Trade"]
                & df[exit_column].notna()
                & (df[exit_column] < 0)
            ].copy()

            late_exits = (
                late_exits
                .sort_values(
                    exit_column,
                    ascending=True,
                )
                .head(self.TOP_N)
                .copy()
            )

            late_exits = self._prepare_section(
                late_exits,
                "TOP_LATE_EXITS",
                exit_column,
            )

            sections.append(
                late_exits
            )

        #
        # ============================================================
        # TOP 20 LATE RE-ENTRIES
        # ============================================================
        #
        # A late re-entry has a positive Re-entry Timing value.
        #
        # Example:
        #
        #     +30% = we re-entered 30% above the recent 10-day low.
        #
        # Larger positive = worse.
        #
        # Again, only actual portfolio trades are included.
        #

        if reentry_column:

            late_entries = df[
                df["Trade"]
                & df[reentry_column].notna()
                & (df[reentry_column] > 0)
            ].copy()

            late_entries = (
                late_entries
                .sort_values(
                    reentry_column,
                    ascending=False,
                )
                .head(self.TOP_N)
                .copy()
            )

            late_entries = self._prepare_section(
                late_entries,
                "TOP_LATE_RE-ENTRIES",
                reentry_column,
            )

            sections.append(
                late_entries
            )

        #
        # ============================================================
        # TOP 20 WHIPSAWS
        # ============================================================
        #
        # Whipsaws are already identified by the transition timing
        # analyzer.
        #
        # Rank by the available economic impact first, rather than
        # treating every whipsaw as equally bad.
        #

        whipsaws = df[
            df["Whipsaw"]
        ].copy()

        if not whipsaws.empty:

            #
            # Build a diagnostic severity score.
            #
            # This is ONLY for ranking this report. It is not an
            # optimizer objective.
            #

            severity = pd.Series(
                0.0,
                index=whipsaws.index,
            )

            if missed_upside_column:
                severity += (
                    whipsaws[
                        missed_upside_column
                    ]
                    .fillna(0)
                    .abs()
                )

            if exit_column:
                severity += (
                    whipsaws[
                        exit_column
                    ]
                    .fillna(0)
                    .abs()
                )

            if reentry_column:
                severity += (
                    whipsaws[
                        reentry_column
                    ]
                    .fillna(0)
                    .abs()
                )

            whipsaws[
                "Whipsaw Severity"
            ] = severity

            whipsaws = (
                whipsaws
                .sort_values(
                    "Whipsaw Severity",
                    ascending=False,
                )
                .head(self.TOP_N)
                .copy()
            )

            whipsaws = self._prepare_section(
                whipsaws,
                "TOP_WHIPSAWS",
                "Whipsaw Severity",
            )

            sections.append(
                whipsaws
            )

        #
        # ============================================================
        # COMBINE SECTIONS
        # ============================================================
        #

        if not sections:
            raise ValueError(
                "No opportunity sections could be generated. "
                "Check the timing columns in "
                "transition_analytics_detailed.csv."
            )

        output = pd.concat(
            sections,
            ignore_index=True,
        )

        #
        # Put the most useful fields first.
        #

        preferred_columns = [
            "Section",
            "Rank",
            "Strategy",
            "Date",
            "Actual Trading Date",
            "Event",
            "From State",
            "To State",
            "From Asset",
            "To Asset",
            "Trade",
            "Whipsaw",
            "Duration Days",
            "Exit Timing",
            "Re-entry Timing",
            "Missed Upside",
            "Downside Avoided",
            "Whipsaw Severity",
        ]

        columns = [
            column
            for column in preferred_columns
            if column in output.columns
        ]

        remaining = [
            column
            for column in output.columns
            if column not in columns
        ]

        output = output[
            columns + remaining
        ]

        #
        # Write output.
        #

        output_path = (
            Path("output")
            / filename
        )

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        output.to_csv(
            output_path,
            index=False,
        )

        return output_path

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _find_column(
        df,
        candidates,
    ):
        """Return the first matching column name."""

        normalized = {
            str(column)
            .strip()
            .lower()
            .replace("_", " ")
            for column in df.columns
        }

        for candidate in candidates:

            candidate_normalized = (
                candidate
                .strip()
                .lower()
                .replace("_", " ")
            )

            for column in df.columns:

                if (
                    str(column)
                    .strip()
                    .lower()
                    .replace("_", " ")
                    == candidate_normalized
                ):
                    return column

        return None

    @staticmethod
    def _numeric(series):
        """
        Convert percentage-looking strings and normal numeric
        values into floats.

        12.5% becomes 0.125.
        """

        if pd.api.types.is_numeric_dtype(series):
            return series.astype(float)

        values = (
            series
            .astype(str)
            .str.strip()
        )

        has_percent = values.str.endswith("%")

        values = (
            values
            .str.replace(
                "%",
                "",
                regex=False,
            )
            .str.replace(
                ",",
                "",
                regex=False,
            )
        )

        result = pd.to_numeric(
            values,
            errors="coerce",
        )

        #
        # Percentage strings are stored as decimal fractions.
        #

        result.loc[has_percent] = (
            result.loc[has_percent] / 100.0
        )

        return result

    @staticmethod
    def _to_bool(value):
        """Convert common CSV boolean representations."""

        if pd.isna(value):
            return False

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return bool(value)

        return str(value).strip().lower() in {
            "true",
            "1",
            "yes",
            "y",
        }

    def _prepare_section(
        self,
        df,
        section_name,
        sort_column,
    ):
        """Add section name and rank."""

        df = df.copy()

        df.insert(
            0,
            "Rank",
            range(
                1,
                len(df) + 1,
            ),
        )

        df.insert(
            0,
            "Section",
            section_name,
        )

        return df