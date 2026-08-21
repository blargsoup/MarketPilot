"""
Rank transition timing opportunities and historical failures.

The authoritative source is transition_analytics_detailed.csv.

The report produces six sections:

    TOP_LATE_EXITS
    TOP_LATE_RE-ENTRIES
    TOP_WHIPSAWS

    BY_STRATEGY_LATE_EXITS
    BY_STRATEGY_LATE_RE-ENTRIES
    BY_STRATEGY_WHIPSAWS

The TOP_* sections deduplicate identical historical signal events
across strategy variants.

The BY_STRATEGY_* sections retain the individual strategy results.
"""

from pathlib import Path

import pandas as pd


class TransitionOpportunityReport:
    """Generate ranked transition opportunity diagnostics."""

    TOP_N = 20

    def generate(
        self,
        detailed_path="output/transition_analytics_detailed.csv",
        filename="transition_opportunities.csv",
    ):
        """
        Generate the opportunity report.

        Parameters
        ----------
        detailed_path:
            Authoritative transition analytics detail CSV.

        filename:
            Output filename under output/.
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

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        self._validate_columns(df)

        #
        # Normalize fields.
        #

        df["Trade"] = df["Trade"].apply(
            self._to_bool
        )

        df["Whipsaw"] = df["Whipsaw"].apply(
            self._to_bool
        )

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

        downside_column = self._find_column(
            df,
            [
                "Downside Avoided",
                "Downside Avoided %",
            ],
        )

        transition_quality_column = self._find_column(
            df,
            [
                "Transition Quality",
            ],
        )

        if exit_column:
            df[exit_column] = self._numeric(
                df[exit_column]
            )

        if reentry_column:
            df[reentry_column] = self._numeric(
                df[reentry_column]
            )

        if downside_column:
            df[downside_column] = self._numeric(
                df[downside_column]
            )

        if transition_quality_column:
            df[transition_quality_column] = self._numeric(
                df[transition_quality_column]
            )

        #
        # Make Downside Avoided positive.
        #
        # The source currently represents this as the defensive
        # period's negative return. For diagnostics, "downside
        # avoided" should read as a positive magnitude.
        #

        if downside_column:
            df["Downside Avoided"] = (
                df[downside_column]
                .abs()
            )

        #
        # Build the six sections.
        #

        sections = []

        #
        # ============================================================
        # UNIQUE HISTORICAL EVENTS
        # ============================================================
        #

        unique_events = self._build_unique_events(
            df,
            exit_column,
            reentry_column,
            transition_quality_column,
        )

        #
        # Top late exits.
        #

        if exit_column:

            late_exits = unique_events[
                unique_events[exit_column].notna()
                & (unique_events[exit_column] < 0)
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

            sections.append(
                self._prepare_section(
                    late_exits,
                    "TOP_LATE_EXITS",
                )
            )

        #
        # Top late re-entries.
        #

        if reentry_column:

            late_entries = unique_events[
                unique_events[reentry_column].notna()
                & (unique_events[reentry_column] > 0)
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

            sections.append(
                self._prepare_section(
                    late_entries,
                    "TOP_LATE_RE-ENTRIES",
                )
            )

        #
        # Top unique whipsaws.
        #

        unique_whipsaws = unique_events[
            unique_events["Whipsaw"]
        ].copy()

        if not unique_whipsaws.empty:

            unique_whipsaws[
                "Whipsaw Severity"
            ] = self._calculate_whipsaw_severity(
                unique_whipsaws,
                exit_column,
                reentry_column,
            )

            unique_whipsaws = (
                unique_whipsaws
                .sort_values(
                    "Whipsaw Severity",
                    ascending=False,
                )
                .head(self.TOP_N)
                .copy()
            )

            sections.append(
                self._prepare_section(
                    unique_whipsaws,
                    "TOP_WHIPSAWS",
                )
            )

        #
        # ============================================================
        # STRATEGY-SPECIFIC RESULTS
        # ============================================================
        #

        #
        # Late exits by strategy.
        #

        if exit_column:

            strategy_exits = df[
                df["Trade"]
                & df[exit_column].notna()
                & (df[exit_column] < 0)
            ].copy()

            strategy_exits[
                "Rank"
            ] = (
                strategy_exits
                .groupby("Strategy")[
                    exit_column
                ]
                .rank(
                    method="first",
                    ascending=True,
                )
            )

            strategy_exits = strategy_exits[
                strategy_exits["Rank"] <= self.TOP_N
            ].copy()

            strategy_exits[
                "Section"
            ] = "BY_STRATEGY_LATE_EXITS"

            sections.append(
                strategy_exits
            )

        #
        # Late re-entries by strategy.
        #

        if reentry_column:

            strategy_entries = df[
                df["Trade"]
                & df[reentry_column].notna()
                & (df[reentry_column] > 0)
            ].copy()

            strategy_entries[
                "Rank"
            ] = (
                strategy_entries
                .groupby("Strategy")[
                    reentry_column
                ]
                .rank(
                    method="first",
                    ascending=False,
                )
            )

            strategy_entries = strategy_entries[
                strategy_entries["Rank"] <= self.TOP_N
            ].copy()

            strategy_entries[
                "Section"
            ] = "BY_STRATEGY_LATE_RE-ENTRIES"

            sections.append(
                strategy_entries
            )

        #
        # Whipsaws by strategy.
        #

        strategy_whipsaws = df[
            df["Whipsaw"]
        ].copy()

        if not strategy_whipsaws.empty:

            strategy_whipsaws[
                "Whipsaw Severity"
            ] = self._calculate_whipsaw_severity(
                strategy_whipsaws,
                exit_column,
                reentry_column,
            )

            strategy_whipsaws[
                "Rank"
            ] = (
                strategy_whipsaws
                .groupby("Strategy")[
                    "Whipsaw Severity"
                ]
                .rank(
                    method="first",
                    ascending=False,
                )
            )

            strategy_whipsaws = strategy_whipsaws[
                strategy_whipsaws["Rank"] <= self.TOP_N
            ].copy()

            strategy_whipsaws[
                "Section"
            ] = "BY_STRATEGY_WHIPSAWS"

            sections.append(
                strategy_whipsaws
            )

        if not sections:
            raise ValueError(
                "No opportunity sections could be generated."
            )

        #
        # ============================================================
        # COMBINE
        # ============================================================
        #

        output = pd.concat(
            sections,
            ignore_index=True,
        )

        #
        # Order the columns.
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
            "Downside Avoided",
            "Whipsaw Severity",
            "Transition Quality",
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
        # Sort the strategy-specific sections sensibly.
        #

        output = self._sort_output(
            output
        )

        #
        # Write file.
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
    # Unique event construction
    # ------------------------------------------------------------------

    def _build_unique_events(
        self,
        df,
        exit_column,
        reentry_column,
        transition_quality_column,
    ):
        """
        Collapse identical historical signal events.

        Strategy variants that experienced the same transition on the
        same trading date are treated as one historical event.

        The primary event is selected using this preference:

            1. NASDAQ 2-State Cash
            2. NASDAQ 2-State
            3. NASDAQ
            4. first available strategy

        Other strategy results are preserved in aggregate columns.
        """

        working = df.copy()

        #
        # Identify the best reference row for each event.
        #

        working[
            "_strategy_priority"
        ] = working["Strategy"].apply(
            self._strategy_priority
        )

        #
        # These fields define a signal event rather than a portfolio
        # implementation.
        #

        event_columns = [
            column
            for column in [
                "Date",
                "Actual Trading Date",
                "From State",
                "To State",
            ]
            if column in working.columns
        ]

        if not event_columns:
            raise ValueError(
                "Unable to identify historical event columns."
            )

        working = working.sort_values(
            "_strategy_priority",
            ascending=True,
        )

        unique = (
            working
            .drop_duplicates(
                subset=event_columns,
                keep="first",
            )
            .copy()
        )

        #
        # Add a count of strategy variants that experienced the event.
        #

        counts = (
            working
            .groupby(event_columns)
            .size()
            .rename(
                "Strategy Variants"
            )
            .reset_index()
        )

        unique = unique.merge(
            counts,
            on=event_columns,
            how="left",
        )

        #
        # Capture the strategy names involved.
        #

        names = (
            working
            .groupby(event_columns)[
                "Strategy"
            ]
            .apply(
                lambda values: " | ".join(
                    dict.fromkeys(
                        values.astype(str)
                    )
                )
            )
            .rename(
                "Strategies Affected"
            )
            .reset_index()
        )

        unique = unique.merge(
            names,
            on=event_columns,
            how="left",
        )

        #
        # Keep the primary strategy label for readability.
        #

        return unique

    @staticmethod
    def _strategy_priority(name):
        """Prefer the current benchmark strategy."""

        name = str(name)

        priorities = {
            "A-RVol v3 (NASDAQ 2-State Cash)": 0,
            "A-RVol v3 (NASDAQ 2-State)": 1,
            "A-RVol v3 (NASDAQ)": 2,
        }

        return priorities.get(
            name,
            100,
        )

    # ------------------------------------------------------------------
    # Whipsaw ranking
    # ------------------------------------------------------------------

    @staticmethod
    def _calculate_whipsaw_severity(
        df,
        exit_column,
        reentry_column,
    ):
        """
        Calculate a diagnostic whipsaw severity.

        This is a ranking aid only. It is deliberately not treated as
        an optimizer objective.
        """

        severity = pd.Series(
            0.0,
            index=df.index,
        )

        if exit_column:
            severity += (
                df[exit_column]
                .fillna(0)
                .abs()
            )

        if reentry_column:
            severity += (
                df[reentry_column]
                .fillna(0)
                .abs()
            )

        return severity

    # ------------------------------------------------------------------
    # Output helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _prepare_section(
        df,
        section_name,
    ):
        """Add section label and sequential rank."""

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

    @staticmethod
    def _sort_output(df):
        """Keep sections grouped and ranked."""

        section_order = {
            "TOP_LATE_EXITS": 0,
            "TOP_LATE_RE-ENTRIES": 1,
            "TOP_WHIPSAWS": 2,
            "BY_STRATEGY_LATE_EXITS": 3,
            "BY_STRATEGY_LATE_RE-ENTRIES": 4,
            "BY_STRATEGY_WHIPSAWS": 5,
        }

        df = df.copy()

        df[
            "_section_order"
        ] = df["Section"].map(
            section_order
        ).fillna(99)

        df = df.sort_values(
            [
                "_section_order",
                "Strategy",
                "Rank",
            ],
            kind="stable",
        )

        return df.drop(
            columns="_section_order"
        )

    # ------------------------------------------------------------------
    # General helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_columns(df):
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

    @staticmethod
    def _find_column(
        df,
        candidates,
    ):
        for candidate in candidates:

            normalized_candidate = (
                candidate
                .strip()
                .lower()
                .replace("_", " ")
            )

            for column in df.columns:

                normalized_column = (
                    str(column)
                    .strip()
                    .lower()
                    .replace("_", " ")
                )

                if (
                    normalized_column
                    == normalized_candidate
                ):
                    return column

        return None

    @staticmethod
    def _numeric(series):
        """Convert numbers and percentage strings to decimals."""

        if pd.api.types.is_numeric_dtype(series):
            return series.astype(float)

        values = (
            series
            .astype(str)
            .str.strip()
        )

        percent = values.str.endswith("%")

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

        result.loc[percent] = (
            result.loc[percent] / 100.0
        )

        return result

    @staticmethod
    def _to_bool(value):
        if pd.isna(value):
            return False

        if isinstance(value, bool):
            return value

        if isinstance(value, (int, float)):
            return bool(value)

        return (
            str(value)
            .strip()
            .lower()
            in {
                "true",
                "1",
                "yes",
                "y",
            }
        )