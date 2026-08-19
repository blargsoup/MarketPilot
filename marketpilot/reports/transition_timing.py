"""
Asset-aware transition timing analytics.

Measures the quality of state transitions using the actual asset
being entered or exited rather than portfolio equity.

Important:
    Forward-looking measurements are bounded by the next state
    transition. A transition can never be judged using market action
    that occurred after the strategy had already changed state.

This module is intended to support:
    - transition timing diagnostics
    - whipsaw detection
    - early/late entry analysis
    - early/late exit analysis
    - eventual strategy optimization
"""

from dataclasses import dataclass
from typing import Optional

import pandas as pd


@dataclass
class TransitionTiming:
    date: pd.Timestamp
    exit_date: Optional[pd.Timestamp]

    from_state: str
    to_state: str

    exited_asset: str
    entered_asset: str

    duration_days: int
    whipsaw: bool

    entry_price: Optional[float]
    exit_price: Optional[float]

    previous_10d_high: Optional[float]
    following_10d_low: Optional[float]

    entry_vs_10d_low: Optional[float]
    exit_vs_previous_10d_high: Optional[float]

    return_1d: Optional[float]
    return_3d: Optional[float]
    return_5d: Optional[float]
    return_10d: Optional[float]
    return_20d: Optional[float]

    mae: Optional[float]
    mfe: Optional[float]

    downside_avoided: Optional[float]
    upside_captured: Optional[float]

    timing_score: Optional[float]
    outcome_score: Optional[float]
    transition_quality: Optional[float]

    timing_class: str


class TransitionTimingAnalyzer:
    """
    Analyze transition quality using actual held assets.

    Parameters
    ----------
    short_transition_days:
        Transitions lasting this many trading days or fewer are
        classified as potential whipsaws.

    lookahead_days:
        Maximum forward window for entry/outcome measurements.

    entry_asset_lookup:
        Optional mapping from state name to asset symbol.

    Example:

        {
            "AGGRESSIVE": "TQQQ",
            "MODERATE": "QLD",
            "DEFENSIVE": "CASH",
        }
    """

    def __init__(
        self,
        short_transition_days: int = 5,
        lookahead_days: int = 20,
    ):
        self.short_transition_days = (
            short_transition_days
        )

        self.lookahead_days = (
            lookahead_days
        )

    # ================================================================
    # PUBLIC API
    # ================================================================

    def analyze(
        self,
        market,
        states: pd.Series,
        state_assets: dict[str, str],
    ) -> list[TransitionTiming]:
        """
        Analyze every state transition.

        Parameters
        ----------
        market:
            Market history dictionary.

        states:
            Series indexed by trading date containing state names.

        state_assets:
            Mapping of state name -> actual asset symbol.

        Returns
        -------
        list[TransitionTiming]
        """

        state_frame = self._prepare_states(
            states
        )

        transitions = (
            self._find_transitions(
                state_frame
            )
        )

        results = []

        for transition in transitions:

            result = self._analyze_transition(
                market,
                state_frame,
                transition,
                state_assets,
            )

            results.append(result)

        return results

    # ================================================================
    # STATE PREPARATION
    # ================================================================

    def _prepare_states(
        self,
        states: pd.Series,
    ) -> pd.Series:

        result = states.copy()

        result.index = pd.to_datetime(
            result.index
        )

        result = result.sort_index()

        result = result.dropna()

        return result

    # ================================================================
    # TRANSITION DETECTION
    # ================================================================

    def _find_transitions(
        self,
        states: pd.Series,
    ) -> list[dict]:

        transitions = []

        previous_state = None

        for position, (date, state) in enumerate(
            states.items()
        ):

            if previous_state is not None:

                if state != previous_state:

                    transitions.append(
                        {
                            "position": position,
                            "date": date,
                            "from_state": previous_state,
                            "to_state": state,
                        }
                    )

            previous_state = state

        return transitions

    # ================================================================
    # TRANSITION ANALYSIS
    # ================================================================

    def _analyze_transition(
        self,
        market,
        states: pd.Series,
        transition: dict,
        state_assets: dict[str, str],
    ) -> TransitionTiming:

        position = transition["position"]

        date = transition["date"]

        from_state = transition["from_state"]

        to_state = transition["to_state"]

        #
        # Asset held before the transition.
        #

        exited_asset = state_assets.get(
            from_state,
            "UNKNOWN",
        )

        #
        # Asset entered by the transition.
        #

        entered_asset = state_assets.get(
            to_state,
            "UNKNOWN",
        )

        #
        # Find next transition.
        #

        next_transition = self._next_transition(
            states,
            position,
        )

        if next_transition is None:

            end_position = len(states) - 1

            exit_date = None

        else:

            end_position = (
                next_transition["position"] - 1
            )

            exit_date = (
                next_transition["date"]
            )

        duration_days = (
            end_position
            - position
            + 1
        )

        whipsaw = (
            duration_days
            <= self.short_transition_days
        )

        #
        # Entry asset price history.
        #

        entry_history = self._history(
            market,
            entered_asset,
        )

        #
        # Exit asset price history.
        #

        exit_history = self._history(
            market,
            exited_asset,
        )

        #
        # Entry price.
        #

        entry_price = self._price_on_date(
            entry_history,
            date,
        )

        #
        # Exit price.
        #
        # The exit happens on the next transition date.
        #

        exit_price = None

        if exit_date is not None:

            exit_price = self._price_on_date(
                exit_history,
                exit_date,
            )

        #
        # Entry timing.
        #

        following_10d_low = (
            self._following_low(
                entry_history,
                date,
                states,
                position,
                end_position,
            )
        )

        entry_vs_10d_low = (
            self._distance_from_low(
                entry_price,
                following_10d_low,
            )
        )

        #
        # Exit timing.
        #

        previous_10d_high = (
            self._previous_high(
                exit_history,
                exit_date,
            )
            if exit_date is not None
            else None
        )

        exit_vs_previous_10d_high = (
            self._distance_from_high(
                exit_price,
                previous_10d_high,
            )
        )

        #
        # Returns while the transition remained active.
        #
        # These use portfolio-equity-equivalent asset returns
        # for the asset that was entered.
        #

        returns = self._forward_returns(
            entry_history,
            date,
            states,
            position,
            end_position,
        )

        #
        # Maximum adverse/favorable excursion after entry.
        #

        mae, mfe = self._excursions(
            entry_history,
            date,
            states,
            position,
            end_position,
        )

        #
        # Outcome measurements.
        #

        downside_avoided = (
            self._downside_avoided(
                exit_history,
                exit_date,
            )
            if exit_date is not None
            else None
        )

        upside_captured = (
            self._upside_captured(
                entry_history,
                date,
                states,
                position,
                end_position,
            )
        )

        #
        # Scores.
        #

        timing_score = self._timing_score(
            from_state=from_state,
            to_state=to_state,
            entry_vs_10d_low=(
                entry_vs_10d_low
            ),
            exit_vs_previous_10d_high=(
                exit_vs_previous_10d_high
            ),
        )

        outcome_score = self._outcome_score(
            to_state=to_state,
            returns=returns,
            downside_avoided=(
                downside_avoided
            ),
            upside_captured=(
                upside_captured
            ),
        )

        transition_quality = (
            self._transition_quality(
                timing_score,
                outcome_score,
            )
        )

        timing_class = self._timing_class(
            timing_score
        )

        return TransitionTiming(
            date=date,
            exit_date=exit_date,

            from_state=from_state,
            to_state=to_state,

            exited_asset=exited_asset,
            entered_asset=entered_asset,

            duration_days=duration_days,
            whipsaw=whipsaw,

            entry_price=entry_price,
            exit_price=exit_price,

            previous_10d_high=(
                previous_10d_high
            ),

            following_10d_low=(
                following_10d_low
            ),

            entry_vs_10d_low=(
                entry_vs_10d_low
            ),

            exit_vs_previous_10d_high=(
                exit_vs_previous_10d_high
            ),

            return_1d=returns[1],
            return_3d=returns[3],
            return_5d=returns[5],
            return_10d=returns[10],
            return_20d=returns[20],

            mae=mae,
            mfe=mfe,

            downside_avoided=(
                downside_avoided
            ),

            upside_captured=(
                upside_captured
            ),

            timing_score=timing_score,
            outcome_score=outcome_score,
            transition_quality=(
                transition_quality
            ),

            timing_class=timing_class,
        )

    # ================================================================
    # MARKET HISTORY
    # ================================================================

    def _history(
        self,
        market,
        symbol: str,
    ):

        if symbol in (
            None,
            "UNKNOWN",
            "CASH",
        ):
            return None

        if symbol not in market:
            return None

        history = market[symbol]

        return history.data

    # ================================================================
    # PRICE ACCESS
    # ================================================================

    def _price_on_date(
        self,
        history,
        date,
    ) -> Optional[float]:

        if history is None:
            return None

        if date not in history.index:
            return None

        row = history.loc[date]

        if "Close" in row:
            return float(row["Close"])

        if "close" in row:
            return float(row["close"])

        return None

    # ================================================================
    # TRANSITION BOUNDARY
    # ================================================================

    def _next_transition(
        self,
        states: pd.Series,
        current_position: int,
    ) -> Optional[dict]:

        current_state = states.iloc[
            current_position
        ]

        for position in range(
            current_position + 1,
            len(states),
        ):

            if states.iloc[position] != current_state:

                return {
                    "position": position,
                    "date": states.index[position],
                }

        return None

    # ================================================================
    # FORWARD LOW
    # ================================================================

    def _following_low(
        self,
        history,
        entry_date,
        states,
        entry_position,
        end_position,
    ) -> Optional[float]:

        if history is None:
            return None

        if entry_date not in history.index:
            return None

        #
        # Only look forward while this transition remains active.
        #

        end = min(
            entry_position
            + self.lookahead_days,
            end_position,
        )

        dates = states.index[
            entry_position:end + 1
        ]

        prices = history.reindex(
            dates
        )["Close"].dropna()

        if prices.empty:
            return None

        return float(
            prices.min()
        )

    # ================================================================
    # PREVIOUS HIGH
    # ================================================================

    def _previous_high(
        self,
        history,
        exit_date,
    ) -> Optional[float]:

        if history is None:
            return None

        if exit_date not in history.index:
            return None

        position = history.index.get_loc(
            exit_date
        )

        start = max(
            0,
            position - 10,
        )

        window = history.iloc[
            start:position + 1
        ]["Close"]

        if window.empty:
            return None

        return float(
            window.max()
        )

    # ================================================================
    # DISTANCE METRICS
    # ================================================================

    def _distance_from_low(
        self,
        entry_price,
        low,
    ) -> Optional[float]:

        if (
            entry_price is None
            or low is None
            or low == 0
        ):
            return None

        return (
            entry_price / low
            - 1.0
        )

    def _distance_from_high(
        self,
        exit_price,
        high,
    ) -> Optional[float]:

        if (
            exit_price is None
            or high is None
            or high == 0
        ):
            return None

        return (
            exit_price / high
            - 1.0
        )

    # ================================================================
    # FORWARD RETURNS
    # ================================================================

    def _forward_returns(
        self,
        history,
        entry_date,
        states,
        entry_position,
        end_position,
    ) -> dict:

        results = {
            1: None,
            3: None,
            5: None,
            10: None,
            20: None,
        }

        if history is None:
            return results

        if entry_date not in history.index:
            return results

        entry_price = self._price_on_date(
            history,
            entry_date,
        )

        if entry_price is None:
            return results

        for days in results:

            target_position = (
                entry_position + days
            )

            #
            # Never cross the next transition.
            #

            if target_position > end_position:
                continue

            target_date = states.index[
                target_position
            ]

            target_price = (
                self._price_on_date(
                    history,
                    target_date,
                )
            )

            if target_price is None:
                continue

            results[days] = (
                target_price
                / entry_price
                - 1.0
            )

        return results

    # ================================================================
    # MAE / MFE
    # ================================================================

    def _excursions(
        self,
        history,
        entry_date,
        states,
        entry_position,
        end_position,
    ) -> tuple[
        Optional[float],
        Optional[float],
    ]:

        if history is None:
            return None, None

        if entry_date not in history.index:
            return None, None

        entry_price = self._price_on_date(
            history,
            entry_date,
        )

        if entry_price is None:
            return None, None

        end = min(
            entry_position
            + self.lookahead_days,
            end_position,
        )

        dates = states.index[
            entry_position:end + 1
        ]

        prices = history.reindex(
            dates
        )["Close"].dropna()

        if prices.empty:
            return None, None

        returns = (
            prices
            / entry_price
            - 1.0
        )

        mae = float(
            returns.min()
        )

        mfe = float(
            returns.max()
        )

        return mae, mfe

    # ================================================================
    # EXIT OUTCOME
    # ================================================================

    def _downside_avoided(
        self,
        history,
        exit_date,
    ) -> Optional[float]:

        if history is None:
            return None

        if exit_date is None:
            return None

        if exit_date not in history.index:
            return None

        exit_position = history.index.get_loc(
            exit_date
        )

        end = min(
            exit_position
            + self.lookahead_days,
            len(history) - 1,
        )

        exit_price = self._price_on_date(
            history,
            exit_date,
        )

        if exit_price is None:
            return None

        prices = history.iloc[
            exit_position:end + 1
        ]["Close"]

        if prices.empty:
            return None

        lowest = float(
            prices.min()
        )

        return (
            lowest
            / exit_price
            - 1.0
        )

    # ================================================================
    # UPSIDE CAPTURE
    # ================================================================

    def _upside_captured(
        self,
        history,
        entry_date,
        states,
        entry_position,
        end_position,
    ) -> Optional[float]:

        if history is None:
            return None

        if entry_date not in history.index:
            return None

        entry_price = self._price_on_date(
            history,
            entry_date,
        )

        if entry_price is None:
            return None

        end = min(
            entry_position
            + self.lookahead_days,
            end_position,
        )

        dates = states.index[
            entry_position:end + 1
        ]

        prices = history.reindex(
            dates
        )["Close"].dropna()

        if prices.empty:
            return None

        highest = float(
            prices.max()
        )

        return (
            highest
            / entry_price
            - 1.0
        )

    # ================================================================
    # TIMING SCORE
    # ================================================================

    def _timing_score(
        self,
        from_state,
        to_state,
        entry_vs_10d_low,
        exit_vs_previous_10d_high,
    ) -> Optional[float]:

        #
        # Re-entry.
        #
        # 0% above low = 100
        # 10% above low = 80
        # 25% above low = 50
        # 50%+ above low = 0
        #

        if (
            "AGGRESSIVE" in to_state
            or "MODERATE" in to_state
        ):

            if entry_vs_10d_low is None:
                return None

            distance = max(
                0.0,
                entry_vs_10d_low,
            )

            return max(
                0.0,
                100.0
                * (
                    1.0
                    - min(
                        distance,
                        0.50,
                    )
                    / 0.50
                ),
            )

        #
        # Exit.
        #
        # 0% below high = 100
        # 10% below high = 80
        # 25% below high = 50
        # 50%+ below high = 0
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

    # ================================================================
    # OUTCOME SCORE
    # ================================================================

    def _outcome_score(
        self,
        to_state,
        returns,
        downside_avoided,
        upside_captured,
    ) -> Optional[float]:

        #
        # Re-entry:
        #
        # Reward actual upside during the active transition.
        #

        if (
            "AGGRESSIVE" in to_state
            or "MODERATE" in to_state
        ):

            candidates = [
                returns[5],
                returns[10],
                returns[20],
            ]

            candidates = [
                value
                for value in candidates
                if value is not None
            ]

            if not candidates:
                return None

            best = max(
                candidates
            )

            #
            # +25% or better = 100
            # 0% = 50
            # -25% or worse = 0
            #

            return max(
                0.0,
                min(
                    100.0,
                    50.0
                    + best * 200.0,
                ),
            )

        #
        # Exit:
        #
        # Reward downside avoided.
        #

        if "DEFENSIVE" in to_state:

            if downside_avoided is None:
                return None

            #
            # -25% or worse avoided = 100
            # 0% = 50
            # +25% = 0
            #

            return max(
                0.0,
                min(
                    100.0,
                    50.0
                    - downside_avoided * 200.0,
                ),
            )

        return None

    # ================================================================
    # COMBINED QUALITY
    # ================================================================

    def _transition_quality(
        self,
        timing_score,
        outcome_score,
    ) -> Optional[float]:

        if (
            timing_score is None
            or outcome_score is None
        ):
            return None

        #
        # Timing matters slightly more than outcome.
        #
        # Outcome remains important because a technically late
        # transition can still have been highly effective.
        #

        return (
            timing_score * 0.60
            + outcome_score * 0.40
        )

    # ================================================================
    # CLASSIFICATION
    # ================================================================

    def _timing_class(
        self,
        score,
    ) -> str:

        if score is None:
            return "N/A"

        if score >= 85:
            return "EXCELLENT"

        if score >= 70:
            return "GOOD"

        if score >= 50:
            return "FAIR"

        if score >= 30:
            return "POOR"

        return "VERY_POOR"