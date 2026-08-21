"""
Rank the most significant transition timing problems.

Produces three top-20 diagnostic sections:

1. Late exits
2. Late re-entries
3. Whipsaws

The report intentionally uses the already-calculated transition timing
metrics rather than creating a second timing model.
"""

from pathlib import Path

import pandas as pd


class TransitionOpportunityReport:
    """Generate ranked transition timing diagnostics."""

    TOP_N = 20

    def generate(
        self,
        transition_details,
        filename="transition_opportunities.csv",
    ):
        """
        Generate a CSV containing the top timing problems.

        Parameters
        ----------
        transition_details:
            List of tuples:

                (
                    strategy_name,
                    transitions,
                    profile,
                )

        filename:
            Output filename under output/.
        """

        rows = []

        for strategy_name, transitions, profile in transition_details:

            for transition in transitions:

                row = self._transition_to_row(
                    strategy_name,
                    transition,
                )

                if row is not None:
                    rows.append(row)

        if not rows:
            return None

        df = pd.DataFrame(rows)

        sections = []

        #
        # ------------------------------------------------------------
        # Top 20 late exits
        # ------------------------------------------------------------
        #

        late_exits = df[
            df["Exit Timing"].notna()
            & (df["Exit Timing"] < 0)
            & (df["Trade"] == True)
        ].copy()

        late_exits = (
            late_exits
            .sort_values(
                "Exit Timing",
                ascending=True,
            )
            .head(self.TOP_N)
            .copy()
        )

        late_exits.insert(
            0,
            "Rank",
            range(1, len(late_exits) + 1),
        )

        late_exits.insert(
            0,
            "Section",
            "TOP_LATE_EXITS",
        )

        sections.append(late_exits)

        #
        # ------------------------------------------------------------
        # Top 20 late re-entries
        # ------------------------------------------------------------
        #

        late_entries = df[
            df["Re-entry Timing"].notna()
            & (df["Re-entry Timing"] > 0)
            & (df["Trade"] == True)
        ].copy()

        late_entries = (
            late_entries
            .sort_values(
                "Re-entry Timing",
                ascending=False,
            )
            .head(self.TOP_N)
            .copy()
        )

        late_entries.insert(
            0,
            "Rank",
            range(1, len(late_entries) + 1),
        )

        late_entries.insert(
            0,
            "Section",
            "TOP_LATE_RE-ENTRIES",
        )

        sections.append(late_entries)

        #
        # ------------------------------------------------------------
        # Top 20 whipsaws
        # ------------------------------------------------------------
        #
        # Whipsaws are already identified by the transition
        # analytics. Rank them by the combined magnitude of:
        #
        #   missed upside
        #   late re-entry
        #   exit timing
        #
        # This is deliberately a diagnostic severity score rather
        # than a portfolio-performance metric.
        #

        whipsaws = df[
            df["Whipsaw"] == True
        ].copy()

        if not whipsaws.empty:

            whipsaws["Whipsaw Severity"] = (
                whipsaws["Missed Upside"].fillna(0).abs()
                + whipsaws["Re-entry Timing"].fillna(0).abs()
                + whipsaws["Exit Timing"].fillna(0).abs()
            )

            whipsaws = (
                whipsaws
                .sort_values(
                    "Whipsaw Severity",
                    ascending=False,
                )
                .head(self.TOP_N)
                .copy()
            )

        whipsaws.insert(
            0,
            "Rank",
            range(1, len(whipsaws) + 1),
        )

        whipsaws.insert(
            0,
            "Section",
            "TOP_WHIPSAWS",
        )

        sections.append(whipsaws)

        #
        # ------------------------------------------------------------
        # Combine
        # ------------------------------------------------------------
        #

        output = pd.concat(
            sections,
            ignore_index=True,
        )

        #
        # Put the most useful columns first.
        #

        preferred_columns = [
            "Section",
            "Rank",
            "Strategy",
            "Date",
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

    def _transition_to_row(
        self,
        strategy_name,
        transition,
    ):
        """
        Convert a transition object into the common diagnostic
        representation.

        This intentionally reads attributes defensively so the report
        remains compatible with the transition dataclass as we add
        analytics.
        """

        def get(name, default=None):
            return getattr(
                transition,
                name,
                default,
            )

        return {
            "Strategy": strategy_name,
            "Date": get("date"),
            "From State": get("from_state"),
            "To State": get("to_state"),
            "From Asset": get("from_asset"),
            "To Asset": get("to_asset"),
            "Trade": bool(
                get("trade", False)
            ),
            "Whipsaw": bool(
                get("whipsaw", False)
            ),
            "Duration Days": get(
                "duration_days"
            ),
            "Exit Timing": get(
                "exit_timing"
            ),
            "Re-entry Timing": get(
                "reentry_timing",
                get("re_entry_timing"),
            ),
            "Missed Upside": get(
                "missed_upside"
            ),
            "Downside Avoided": get(
                "downside_avoided"
            ),
        }