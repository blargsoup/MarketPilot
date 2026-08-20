"""
Higher-level transition analytics.

Consumes TransitionTiming objects and produces:
    - transition counts
    - whipsaw rates
    - exit timing
    - re-entry timing
    - defensive duration
    - missed upside
    - avoided downside

Also supports historical period segmentation.

This module intentionally does NOT modify the strategy or rebuild
the backtest. It is purely analytical.
"""

from dataclasses import dataclass

import pandas as pd

from .analysis_periods import ANALYSIS_PERIODS


@dataclass
class TransitionAggregate:
    strategy: str
    period: str

    transitions: int
    whipsaws: int
    whipsaw_rate: float | None

    average_exit_timing: float | None
    median_exit_timing: float | None

    average_reentry_timing: float | None
    median_reentry_timing: float | None

    average_defensive_duration: float | None
    median_defensive_duration: float | None

    average_missed_upside: float | None
    median_missed_upside: float | None

    average_avoided_downside: float | None
    median_avoided_downside: float | None

    average_transition_quality: float | None


class TransitionAnalytics:
    """
    Aggregate transition-level analytics.

    A TransitionTiming object represents one actual state change.
    This class deliberately works from those actual transitions rather
    than reconstructing signals.
    """

    def analyze(
        self,
        transitions,
        strategy_name="",
    ):
        """
        Return one aggregate for the complete transition set.
        """

        return self._aggregate(
            transitions,
            strategy_name,
            "FULL",
        )

    def analyze_periods(
        self,
        transitions,
        strategy_name="",
    ):
        """
        Return aggregates for all configured historical periods.
        """

        results = []

        for period_name, definition in ANALYSIS_PERIODS.items():

            filtered = self._filter_period(
                transitions,
                definition["start"],
                definition["end"],
            )

            results.append(
                self._aggregate(
                    filtered,
                    strategy_name,
                    period_name,
                )
            )

        return results

    # ================================================================
    # AGGREGATION
    # ================================================================

    def _aggregate(
        self,
        transitions,
        strategy_name,
        period_name,
    ):

        transitions = list(transitions)

        if not transitions:
            return TransitionAggregate(
                strategy=strategy_name,
                period=period_name,

                transitions=0,
                whipsaws=0,
                whipsaw_rate=None,

                average_exit_timing=None,
                median_exit_timing=None,

                average_reentry_timing=None,
                median_reentry_timing=None,

                average_defensive_duration=None,
                median_defensive_duration=None,

                average_missed_upside=None,
                median_missed_upside=None,

                average_avoided_downside=None,
                median_avoided_downside=None,

                average_transition_quality=None,
            )

        frame = pd.DataFrame(
            [
                {
                    "date": t.date,

                    "from_state": t.from_state,
                    "to_state": t.to_state,

                    "whipsaw": t.whipsaw,

                    "duration": t.duration_days,

                    "entry_timing": (
                        t.entry_vs_10d_low
                        if self._is_reentry(t)
                        else None
                    ),

                    "exit_timing": (
                        t.exit_vs_previous_10d_high
                        if self._is_exit(t)
                        else None
                    ),

                    "missed_upside": (
                        self._missed_upside(t)
                    ),

                    "avoided_downside": (
                        self._avoided_downside(t)
                    ),

                    "quality": (
                        t.transition_quality
                    ),
                }
                for t in transitions
            ]
        )

        exits = frame[
            frame["exit_timing"].notna()
        ]

        entries = frame[
            frame["entry_timing"].notna()
        ]

        defensive = frame[
            frame["to_state"] == "DEFENSIVE"
        ]

        return TransitionAggregate(
            strategy=strategy_name,
            period=period_name,

            transitions=len(frame),

            whipsaws=int(
                frame["whipsaw"].sum()
            ),

            whipsaw_rate=self._mean(
                frame["whipsaw"]
            ),

            average_exit_timing=self._mean(
                exits["exit_timing"]
            ),

            median_exit_timing=self._median(
                exits["exit_timing"]
            ),

            average_reentry_timing=self._mean(
                entries["entry_timing"]
            ),

            median_reentry_timing=self._median(
                entries["entry_timing"]
            ),

            average_defensive_duration=self._mean(
                defensive["duration"]
            ),

            median_defensive_duration=self._median(
                defensive["duration"]
            ),

            average_missed_upside=self._mean(
                frame["missed_upside"]
            ),

            median_missed_upside=self._median(
                frame["missed_upside"]
            ),

            average_avoided_downside=self._mean(
                frame["avoided_downside"]
            ),

            median_avoided_downside=self._median(
                frame["avoided_downside"]
            ),

            average_transition_quality=self._mean(
                frame["quality"]
            ),
        )

    # ================================================================
    # CLASSIFICATION
    # ================================================================

    @staticmethod
    def _is_exit(transition):

        return (
            transition.to_state
            == "DEFENSIVE"
        )

    @staticmethod
    def _is_reentry(transition):

        return (
            transition.to_state
            in (
                "AGGRESSIVE",
                "MODERATE",
            )
            and transition.from_state
            == "DEFENSIVE"
        )

    # ================================================================
    # MISSED UPSIDE
    # ================================================================

    @staticmethod
    def _missed_upside(transition):

        """
        For an exit:

            How much favorable movement occurred in the exited
            asset while the strategy was defensive?

        We use the existing MFE-like measurement already calculated
        by TransitionTiming.

        For non-exits there is no missed-upside measurement.
        """

        if not TransitionAnalytics._is_exit(
            transition
        ):
            return None

        if transition.upside_captured is None:
            return None

        return transition.upside_captured

    # ================================================================
    # AVOIDED DOWNSIDE
    # ================================================================

    @staticmethod
    def _avoided_downside(transition):

        """
        The existing downside_avoided metric is negative when the
        exited asset subsequently falls.

        Convert it to a positive "benefit" number.

        Example:

            -0.25 -> +0.25 avoided downside

        If the asset rises instead, the value becomes zero.
        """

        if not TransitionAnalytics._is_exit(
            transition
        ):
            return None

        value = transition.downside_avoided

        if value is None:
            return None

        return max(
            0.0,
            -value,
        )

    # ================================================================
    # PERIOD FILTERING
    # ================================================================

    @staticmethod
    def _filter_period(
        transitions,
        start,
        end,
    ):

        start_date = pd.Timestamp(
            start
        )

        end_date = (
            pd.Timestamp(end)
            if end is not None
            else None
        )

        results = []

        for transition in transitions:

            date = pd.Timestamp(
                transition.date
            )

            if date < start_date:
                continue

            if (
                end_date is not None
                and date >= end_date
            ):
                continue

            results.append(
                transition
            )

        return results

    # ================================================================
    # STATISTICS
    # ================================================================

    @staticmethod
    def _mean(series):

        if series is None:
            return None

        series = pd.Series(
            series
        ).dropna()

        if series.empty:
            return None

        return float(
            series.mean()
        )

    @staticmethod
    def _median(series):

        if series is None:
            return None

        series = pd.Series(
            series
        ).dropna()

        if series.empty:
            return None

        return float(
            series.median()
        )