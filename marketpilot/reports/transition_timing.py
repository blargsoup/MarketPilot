"""
Transition timing analytics.

Evaluates whether strategy state transitions were:

    - early
    - well timed
    - late
    - short-lived / possible whipsaw

The analysis is intentionally transition-aware. Forward-looking
measurements stop at the next strategy state transition, so a
transition is never judged using market movement that occurred after
the strategy had already changed state again.
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class TransitionTiming:
    date: pd.Timestamp
    from_state: str
    to_state: str

    duration_days: int

    # Forward performance while the transition remained active.
    return_1d: Optional[float]
    return_3d: Optional[float]
    return_5d: Optional[float]
    return_10d: Optional[float]
    return_20d: Optional[float]

    # Timing measurements.
    entry_vs_10d_low: Optional[float]
    exit_vs_previous_10d_high: Optional[float]

    # Classification.
    timing_score: Optional[float]
    timing_class: str

    whipsaw: bool


class TransitionTimingAnalyzer:
    """
    Analyze the timing quality of strategy transitions.

    Parameters
    ----------
    short_transition_days:
        A transition lasting this many trading days or fewer is
        considered potentially short-lived / whipsaw.

    lookahead_days:
        Maximum number of trading days used for timing analysis.
    """

    def __init__(
        self,
        short_transition_days: int = 5,
        lookahead_days: int = 20,
    ):
        self.short_transition_days = short_transition_days
        self.lookahead_days = lookahead_days

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        equity: pd.Series,
        states: pd.Series,
    ) -> list[TransitionTiming]:
        """
        Analyze every state transition.

        `equity` must contain the portfolio equity indexed by date.

        `states` must contain the strategy state indexed by date.

        Both series are aligned to their common dates.
        """

        data = self._prepare(
            equity,
            states,
        )

        transitions = self._find_transitions(data)

        results = []

        for transition in transitions:

            result = self._analyze_transition(
                data,
                transition,
            )

            results.append(result)

        return results

    # ------------------------------------------------------------------
    # Preparation
    # ------------------------------------------------------------------

    def _prepare(
        self,
        equity: pd.Series,
        states: pd.Series,
    ) -> pd.DataFrame:

        frame = pd.DataFrame(
            {
                "equity": equity,
                "state": states,
            }
        )

        frame = frame.dropna()

        frame = frame.sort_index()

        return frame

    # ------------------------------------------------------------------
    # Transition detection
    # ------------------------------------------------------------------

    def _find_transitions(
        self,
        data: pd.DataFrame,
    ) -> list[dict]:

        transitions = []

        previous_state = None
        previous_date = None

        for date, row in data.iterrows():

            state = row["state"]

            if previous_state is not None:

                if state != previous_state:

                    transitions.append(
                        {
                            "date": date,
                            "from_state": previous_state,
                            "to_state": state,
                            "previous_date": previous_date,
                        }
                    )

            previous_state = state
            previous_date = date

        return transitions

    # ------------------------------------------------------------------
    # Individual transition
    # ------------------------------------------------------------------

    def _analyze_transition(
        self,
        data: pd.DataFrame,
        transition: dict,
    ) -> TransitionTiming:

        date = transition["date"]

        from_state = transition["from_state"]

        to_state = transition["to_state"]

        entry_position = data.index.get_loc(date)

        #
        # Find the next transition.
        #
        # This is critical.
        #
        # Forward measurements are NOT allowed to cross this boundary.
        #

        next_transition = self._next_transition_index(
            data,
            entry_position,
        )

        if next_transition is None:

            end_position = len(data) - 1

        else:

            end_position = next_transition - 1

        duration_days = (
            end_position
            - entry_position
            + 1
        )

        active = data.iloc[
            entry_position:end_position + 1
        ]

        equity_start = active["equity"].iloc[0]

        returns = {}

        for days in (
            1,
            3,
            5,
            10,
            20,
        ):

            if days < len(active):

                equity_end = active["equity"].iloc[days]

                returns[days] = (
                    equity_end
                    / equity_start
                    - 1
                )

            else:

                returns[days] = None

        #
        # Re-entry timing.
        #
        # When entering a risk asset, we want to know how close the
        # entry was to the lowest point available during the following
        # 10 trading days, but only while the transition remains active.
        #

        entry_vs_10d_low = self._entry_vs_forward_low(
            data,
            entry_position,
            end_position,
        )

        #
        # Exit timing.
        #
        # When exiting risk, compare the exit point to the highest price
        # achieved during the preceding 10 trading days.
        #
        # For portfolio-level analysis we use equity rather than the
        # underlying ETF price.
        #

        exit_vs_previous_10d_high = (
            self._exit_vs_previous_high(
                data,
                entry_position,
            )
        )

        #
        # Timing score.
        #

        timing_score = self._timing_score(
            to_state=to_state,
            entry_vs_10d_low=entry_vs_10d_low,
            exit_vs_previous_10d_high=(
                exit_vs_previous_10d_high
            ),
        )

        timing_class = self._timing_class(
            timing_score,
        )

        whipsaw = (
            duration_days
            <= self.short_transition_days
        )

        return TransitionTiming(
            date=date,
            from_state=from_state,
            to_state=to_state,
            duration_days=duration_days,
            return_1d=returns[1],
            return_3d=returns[3],
            return_5d=returns[5],
            return_10d=returns[10],
            return_20d=returns[20],
            entry_vs_10d_low=entry_vs_10d_low,
            exit_vs_previous_10d_high=(
                exit_vs_previous_10d_high
            ),
            timing_score=timing_score,
            timing_class=timing_class,
            whipsaw=whipsaw,
        )

    # ------------------------------------------------------------------
    # Transition boundaries
    # ------------------------------------------------------------------

    def _next_transition_index(
        self,
        data: pd.DataFrame,
        current_position: int,
    ) -> Optional[int]:

        current_state = data["state"].iloc[
            current_position
        ]

        for position in range(
            current_position + 1,
            len(data),
        ):

            if data["state"].iloc[position] != current_state:

                return position

        return None

    # ------------------------------------------------------------------
    # Entry timing
    # ------------------------------------------------------------------

    def _entry_vs_forward_low(
        self,
        data: pd.DataFrame,
        entry_position: int,
        end_position: int,
    ) -> Optional[float]:

        entry_equity = data["equity"].iloc[
            entry_position
        ]

        forward_end = min(
            entry_position + self.lookahead_days,
            end_position,
        )

        window = data["equity"].iloc[
            entry_position:forward_end + 1
        ]

        if len(window) < 2:
            return None

        low = window.min()

        #
        # Positive means the entry was above the subsequent low.
        #
        # Example:
        #
        # Entry = $100
        # 10d low = $90
        #
        # Result = 11.11%
        #
        # This tells us there was an additional 10% decline available
        # after our entry.
        #

        if low == 0:
            return None

        return (
            entry_equity / low
            - 1
        )

    # ------------------------------------------------------------------
    # Exit timing
    # ------------------------------------------------------------------

    def _exit_vs_previous_high(
        self,
        data: pd.DataFrame,
        exit_position: int,
    ) -> Optional[float]:

        if exit_position == 0:
            return None

        start = max(
            0,
            exit_position - 10,
        )

        window = data["equity"].iloc[
            start:exit_position + 1
        ]

        high = window.max()

        exit_equity = data["equity"].iloc[
            exit_position
        ]

        if high == 0:
            return None

        #
        # Positive means we exited below the recent high.
        #
        # Example:
        #
        # Previous 10d high = $120
        # Exit = $100
        #
        # Result = -16.67%
        #
        # The negative sign is intentional: it represents the amount
        # of value remaining above the exit.
        #

        return (
            exit_equity / high
            - 1
        )

    # ------------------------------------------------------------------
    # Timing score
    # ------------------------------------------------------------------

    def _timing_score(
        self,
        to_state: str,
        entry_vs_10d_low: Optional[float],
        exit_vs_previous_10d_high: Optional[float],
    ) -> Optional[float]:

        #
        # Re-entry:
        #
        # We want a low entry.
        #
        # 0% = entered exactly at the 10d low
        # 5% = entered 5% above the low
        # 20% = entered 20% above the low
        #
        # Lower is better.
        #

        if (
            "AGGRESSIVE" in to_state
            or "MODERATE" in to_state
        ):

            if entry_vs_10d_low is None:
                return None

            penalty = max(
                0.0,
                entry_vs_10d_low,
            )

            return max(
                0.0,
                100.0
                * (
                    1.0
                    - min(
                        penalty,
                        0.50,
                    )
                    / 0.50
                ),
            )

        #
        # Exit:
        #
        # We want to exit close to the previous high.
        #
        # 0% below high = perfect
        # -5% = very good
        # -20% = increasingly late
        #
        #

        if "DEFENSIVE" in to_state:

            if exit_vs_previous_10d_high is None:
                return None

            miss = abs(
                min(
                    0.0,
                    exit_vs_previous_10d_high,
                )
            )

            return max(
                0.0,
                100.0
                * (
                    1.0
                    - min(
                        miss,
                        0.50,
                    )
                    / 0.50
                ),
            )

        return None

    # ------------------------------------------------------------------
    # Classification
    # ------------------------------------------------------------------

    def _timing_class(
        self,
        score: Optional[float],
    ) -> str:

        if score is None:
            return "N/A"

        if score >= 80:
            return "EXCELLENT"

        if score >= 60:
            return "GOOD"

        if score >= 40:
            return "FAIR"

        if score >= 20:
            return "POOR"

        return "VERY_POOR"