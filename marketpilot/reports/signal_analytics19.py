"""
Signal analytics.

Analyzes signal events in the context of actual strategy transitions.

The key rule is that forward-looking measurements never cross a subsequent
state transition. This prevents a signal from being credited/debited for
market behavior that occurred after the strategy had already changed state.
"""

from __future__ import annotations

from dataclasses import dataclass
from collections import defaultdict
from typing import Iterable
import csv
import math
import statistics


@dataclass
class SignalEvent:
    strategy: str
    date: object
    signal: str
    state: str
    asset: str
    equity: float
    rvol: float | None
    vr: float | None
    spy_distance: float | None
    credit: float | None
    transition_reasons: str

    return_5d: float | None = None
    return_20d: float | None = None
    return_60d: float | None = None
    return_120d: float | None = None

    max_gain_20d: float | None = None
    days_to_max_gain_20d: float | None = None
    max_drawdown_20d: float | None = None
    days_to_max_drawdown_20d: float | None = None

    max_gain_60d: float | None = None
    days_to_max_gain_60d: float | None = None
    max_drawdown_60d: float | None = None
    days_to_max_drawdown_60d: float | None = None

    max_gain_120d: float | None = None
    days_to_max_gain_120d: float | None = None
    max_drawdown_120d: float | None = None
    days_to_max_drawdown_120d: float | None = None


class SignalAnalytics:

    def __init__(
        self,
        events: Iterable[dict] | Iterable[SignalEvent],
    ):
        self.events = [
            self._coerce_event(event)
            for event in events
        ]

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        transitions=None,
        state_history=None,
        strategy_name=None,
    ):
        """
        Return attribution rows.

        transitions should contain actual state transitions where possible.
        state_history is optional and may be a mapping of date -> state.
        """

        events = self.events

        if strategy_name:
            events = [
                event
                for event in events
                if event.strategy == strategy_name
            ]

        transition_dates = self._transition_dates(
            transitions
        )

        rows = []

        for event in events:

            next_transition = self._next_transition(
                event.date,
                transition_dates,
            )

            rows.append(
                self._build_attribution(
                    event,
                    next_transition,
                )
            )

        return rows

    def summarize(
        self,
        attribution_rows,
    ):
        """
        Aggregate events by signal / transition reason.
        """

        groups = defaultdict(list)

        for row in attribution_rows:

            signal = row.get(
                "Signal",
                "",
            )

            reasons = row.get(
                "Transition Reasons",
                "",
            )

            key = (
                signal,
                reasons,
            )

            groups[key].append(row)

        summaries = []

        for (
            signal,
            reasons,
        ), rows in groups.items():

            summaries.append(
                self._summarize_group(
                    signal,
                    reasons,
                    rows,
                )
            )

        summaries.sort(
            key=lambda row: (
                row["Signal"],
                row["Transition Reasons"],
            )
        )

        return summaries

    def write_attribution(
        self,
        rows,
        filename,
    ):
        if not rows:
            return

        fieldnames = list(
            rows[0].keys()
        )

        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            writer.writerows(rows)

    def write_summary(
        self,
        rows,
        filename,
    ):
        if not rows:
            return

        fieldnames = list(
            rows[0].keys()
        )

        with open(
            filename,
            "w",
            newline="",
            encoding="utf-8",
        ) as handle:

            writer = csv.DictWriter(
                handle,
                fieldnames=fieldnames,
            )

            writer.writeheader()

            writer.writerows(rows)

    # ------------------------------------------------------------------
    # Attribution
    # ------------------------------------------------------------------

    def _build_attribution(
        self,
        event,
        next_transition,
    ):

        result = {
            "Strategy": event.strategy,
            "Date": self._date_string(event.date),
            "Signal": event.signal,
            "State": event.state,
            "Asset": event.asset,
            "Equity": event.equity,
            "RVol": event.rvol,
            "VR": event.vr,
            "SPY vs 200 SMA": event.spy_distance,
            "Credit": event.credit,
            "Transition Reasons":
                event.transition_reasons,

            "Next Transition":
                self._date_string(next_transition)
                if next_transition
                else "",

            "Days To Transition":
                self._days_between(
                    event.date,
                    next_transition,
                )
                if next_transition
                else "",

            "Transition Boundary":
                "YES"
                if next_transition
                else "NO",
        }

        # --------------------------------------------------------------
        # Forward metrics
        #
        # If a transition occurs before the standard horizon, don't use
        # the full-horizon result.
        # --------------------------------------------------------------

        for horizon in (
            5,
            20,
            60,
            120,
        ):

            days_available = self._available_days(
                event.date,
                next_transition,
                horizon,
            )

            result[
                f"Forward Window {horizon}d"
            ] = days_available

            result[
                f"Return +{horizon}d Valid"
            ] = (
                "YES"
                if days_available >= horizon
                else "NO"
            )

            source_value = getattr(
                event,
                f"return_{horizon}d",
            )

            result[
                f"Asset Return +{horizon}d"
            ] = (
                source_value
                if days_available >= horizon
                else ""
            )

        # --------------------------------------------------------------
        # Existing max excursion metrics
        # --------------------------------------------------------------

        for horizon in (
            20,
            60,
            120,
        ):

            available = self._available_days(
                event.date,
                next_transition,
                horizon,
            )

            if available <= 0:
                continue

            gain = getattr(
                event,
                f"max_gain_{horizon}d",
            )

            drawdown = getattr(
                event,
                f"max_drawdown_{horizon}d",
            )

            gain_day = getattr(
                event,
                f"days_to_max_gain_{horizon}d",
            )

            drawdown_day = getattr(
                event,
                f"days_to_max_drawdown_{horizon}d",
            )

            if available < horizon:

                gain = ""
                drawdown = ""
                gain_day = ""
                drawdown_day = ""

            result[
                f"Max Gain +{horizon}d"
            ] = gain

            result[
                f"Days To Max Gain +{horizon}d"
            ] = gain_day

            result[
                f"Max Drawdown +{horizon}d"
            ] = drawdown

            result[
                f"Days To Max Drawdown +{horizon}d"
            ] = drawdown_day

        # --------------------------------------------------------------
        # Timing diagnostics
        #
        # These are based on the available signal-event diagnostics.
        # --------------------------------------------------------------

        result[
            "Timing Classification"
        ] = self._timing_classification(
            event
        )

        result[
            "Timing Score"
        ] = self._timing_score(
            event
        )

        result[
            "Outcome Score"
        ] = self._outcome_score(
            event
        )

        result[
            "Whipsaw"
        ] = self._is_whipsaw(
            event,
            next_transition,
        )

        result[
            "Timing Quality"
        ] = self._timing_quality(
            event,
            next_transition,
        )

        return result

    # ------------------------------------------------------------------
    # Aggregate summaries
    # ------------------------------------------------------------------

    def _summarize_group(
        self,
        signal,
        reasons,
        rows,
    ):

        returns_5 = self._numbers(
            rows,
            "Asset Return +5d",
        )

        returns_20 = self._numbers(
            rows,
            "Asset Return +20d",
        )

        returns_60 = self._numbers(
            rows,
            "Asset Return +60d",
        )

        returns_120 = self._numbers(
            rows,
            "Asset Return +120d",
        )

        timing = self._numbers(
            rows,
            "Timing Score",
        )

        outcome = self._numbers(
            rows,
            "Outcome Score",
        )

        quality = self._numbers(
            rows,
            "Timing Quality",
        )

        transition_days = self._numbers(
            rows,
            "Days To Transition",
        )

        whipsaws = [
            row
            for row in rows
            if row.get("Whipsaw") == "YES"
        ]

        return {
            "Signal": signal,
            "Transition Reasons": reasons,
            "Events": len(rows),

            "Whipsaws": len(
                whipsaws
            ),

            "Whipsaw %": self._percentage(
                len(whipsaws),
                len(rows),
            ),

            "Avg Transition Days":
                self._mean_or_blank(
                    transition_days
                ),

            "Median Transition Days":
                self._median_or_blank(
                    transition_days
                ),

            "Avg Return +5d":
                self._mean_or_blank(
                    returns_5
                ),

            "Avg Return +20d":
                self._mean_or_blank(
                    returns_20
                ),

            "Avg Return +60d":
                self._mean_or_blank(
                    returns_60
                ),

            "Avg Return +120d":
                self._mean_or_blank(
                    returns_120
                ),

            "Avg Timing Score":
                self._mean_or_blank(
                    timing
                ),

            "Avg Outcome Score":
                self._mean_or_blank(
                    outcome
                ),

            "Avg Timing Quality":
                self._mean_or_blank(
                    quality
                ),

            "Positive 20d %":
                self._positive_percentage(
                    returns_20
                ),

            "Positive 60d %":
                self._positive_percentage(
                    returns_60
                ),

            "Positive 120d %":
                self._positive_percentage(
                    returns_120
                ),
        }

    # ------------------------------------------------------------------
    # Timing
    # ------------------------------------------------------------------

    def _timing_score(
        self,
        event,
    ):
        """
        Normalize timing into approximately -1 to +1.

        For an exit:
            positive = protective / timely exit
            negative = late exit

        For an entry:
            positive = attractive entry
            negative = chasing the move
        """

        gain = event.max_gain_20d
        drawdown = event.max_drawdown_20d

        if gain is None or drawdown is None:
            return ""

        # A signal immediately followed by meaningful adverse movement
        # is generally more useful for an exit.
        #
        # Conversely, a signal followed by strong upside is useful for
        # an entry.
        if event.state == "DEFENSIVE":

            score = (
                -drawdown
                - max(gain, 0.0) * 0.50
            )

        else:

            score = (
                max(gain, 0.0)
                + min(drawdown, 0.0) * 0.50
            )

        return round(
            max(
                -1.0,
                min(
                    1.0,
                    score,
                ),
            ),
            4,
        )

    def _outcome_score(
        self,
        event,
    ):

        values = []

        for horizon in (
            5,
            20,
            60,
        ):

            value = getattr(
                event,
                f"return_{horizon}d",
            )

            if value is not None:
                values.append(
                    value
                )

        if not values:
            return ""

        score = (
            sum(values)
            / len(values)
        )

        return round(
            score,
            4,
        )

    def _timing_classification(
        self,
        event,
    ):

        gain = event.max_gain_20d

        drawdown = event.max_drawdown_20d

        if gain is None or drawdown is None:
            return ""

        if event.state == "DEFENSIVE":

            if drawdown < -0.10:
                return "TIMELY_EXIT"

            if gain > 0.10:
                return "EARLY_EXIT"

            return "NEUTRAL"

        if drawdown < -0.10:
            return "EARLY_ENTRY"

        if gain > 0.10:
            return "GOOD_ENTRY"

        return "NEUTRAL"

    def _timing_quality(
        self,
        event,
        next_transition,
    ):

        classification = (
            self._timing_classification(
                event
            )
        )

        if not classification:
            return ""

        if classification in (
            "TIMELY_EXIT",
            "GOOD_ENTRY",
        ):
            return "GOOD"

        if classification in (
            "EARLY_EXIT",
            "EARLY_ENTRY",
        ):
            return "EARLY"

        return "NEUTRAL"

    def _is_whipsaw(
        self,
        event,
        next_transition,
    ):

        if next_transition is None:
            return "NO"

        days = self._days_between(
            event.date,
            next_transition,
        )

        if days is None:
            return "NO"

        return (
            "YES"
            if days <= 10
            else "NO"
        )

    # ------------------------------------------------------------------
    # Transition helpers
    # ------------------------------------------------------------------

    def _transition_dates(
        self,
        transitions,
    ):

        if transitions is None:
            return []

        dates = []

        for transition in transitions:

            if isinstance(
                transition,
                dict,
            ):

                date = (
                    transition.get("Date")
                    or transition.get("date")
                )

            else:

                date = getattr(
                    transition,
                    "date",
                    None,
                )

            if date is not None:
                dates.append(
                    date
                )

        return sorted(
            dates
        )

    def _next_transition(
        self,
        date,
        transition_dates,
    ):

        for transition_date in transition_dates:

            if transition_date > date:
                return transition_date

        return None

    def _available_days(
        self,
        date,
        next_transition,
        horizon,
    ):

        if next_transition is None:
            return horizon

        delta = self._days_between(
            date,
            next_transition,
        )

        if delta is None:
            return horizon

        return min(
            horizon,
            max(
                0,
                delta,
            ),
        )

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    def _coerce_event(
        self,
        event,
    ):

        if isinstance(
            event,
            SignalEvent,
        ):
            return event

        def number(
            key,
        ):
            value = event.get(
                key
            )

            if value in (
                None,
                "",
            ):
                return None

            try:
                return float(
                    value
                )
            except (
                TypeError,
                ValueError,
            ):
                return None

        return SignalEvent(
            strategy=event.get(
                "Strategy",
                "",
            ),
            date=self._parse_date(
                event.get(
                    "Date"
                )
            ),
            signal=event.get(
                "Signal",
                "",
            ),
            state=event.get(
                "State",
                "",
            ),
            asset=event.get(
                "Asset",
                "",
            ),
            equity=number(
                "Equity"
            ) or 0.0,
            rvol=number(
                "RVol"
            ),
            vr=number(
                "VR"
            ),
            spy_distance=number(
                "SPY vs 200 SMA"
            ),
            credit=number(
                "Credit"
            ),
            transition_reasons=event.get(
                "Transition Reasons",
                "",
            ),

            return_5d=number(
                "Asset Return +5d"
            ),
            return_20d=number(
                "Asset Return +20d"
            ),
            return_60d=number(
                "Asset Return +60d"
            ),
            return_120d=number(
                "Asset Return +120d"
            ),

            max_gain_20d=number(
                "Max Gain +20d"
            ),
            days_to_max_gain_20d=number(
                "Days To Max Gain +20d"
            ),
            max_drawdown_20d=number(
                "Max Drawdown +20d"
            ),
            days_to_max_drawdown_20d=number(
                "Days To Max Drawdown +20d"
            ),

            max_gain_60d=number(
                "Max Gain +60d"
            ),
            days_to_max_gain_60d=number(
                "Days To Max Gain +60d"
            ),
            max_drawdown_60d=number(
                "Max Drawdown +60d"
            ),
            days_to_max_drawdown_60d=number(
                "Days To Max Drawdown +60d"
            ),

            max_gain_120d=number(
                "Max Gain +120d"
            ),
            days_to_max_gain_120d=number(
                "Days To Max Gain +120d"
            ),
            max_drawdown_120d=number(
                "Max Drawdown +120d"
            ),
            days_to_max_drawdown_120d=number(
                "Days To Max Drawdown +120d"
            ),
        )

    # ------------------------------------------------------------------
    # Utilities
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_date(value):

        if value is None:
            return None

        if hasattr(
            value,
            "date",
        ):
            return value

        try:
            import pandas as pd

            return pd.Timestamp(
                value
            )
        except Exception:
            return value

    @staticmethod
    def _date_string(value):

        if value is None:
            return ""

        try:
            return value.strftime(
                "%Y-%m-%d"
            )
        except AttributeError:
            return str(
                value
            )

    @staticmethod
    def _days_between(
        first,
        second,
    ):

        if first is None or second is None:
            return None

        try:
            return (
                second - first
            ).days
        except AttributeError:
            return None

    @staticmethod
    def _numbers(
        rows,
        key,
    ):

        values = []

        for row in rows:

            value = row.get(
                key
            )

            if value in (
                None,
                "",
            ):
                continue

            try:
                values.append(
                    float(
                        value
                    )
                )
            except (
                TypeError,
                ValueError,
            ):
                pass

        return values

    @staticmethod
    def _mean_or_blank(
        values,
    ):

        if not values:
            return ""

        return round(
            statistics.mean(
                values
            ),
            4,
        )

    @staticmethod
    def _median_or_blank(
        values,
    ):

        if not values:
            return ""

        return round(
            statistics.median(
                values
            ),
            4,
        )

    @staticmethod
    def _percentage(
        numerator,
        denominator,
    ):

        if denominator == 0:
            return 0.0

        return round(
            numerator
            / denominator
            * 100,
            2,
        )

    @classmethod
    def _positive_percentage(
        cls,
        values,
    ):

        if not values:
            return ""

        positive = sum(
            1
            for value in values
            if value > 0
        )

        return cls._percentage(
            positive,
            len(values),
        )