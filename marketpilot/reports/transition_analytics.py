"""
Aggregate transition analytics.

Important distinction:

    STATE TRANSITION
        A change in the strategy's internal signal state.

    PORTFOLIO TRANSITION
        A change in the actual asset held by the strategy.

A 2-State strategy may have:

    AGGRESSIVE -> MODERATE

while remaining invested in TQQQ.

That is a state transition, but NOT a trade.

All trade-related analytics in this module therefore use the
portfolio asset transition rather than the state transition.
"""

from dataclasses import dataclass

import pandas as pd

from .analysis_periods import ANALYSIS_PERIODS


@dataclass
class TransitionAggregate:
    strategy: str
    period: str

    state_transitions: int
    trades: int

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
    Aggregate TransitionTiming records.

    The analyzer receives both:
        - the transition records
        - the strategy profile

    so it can determine whether each state transition actually
    changes the portfolio position.
    """

    def analyze(
        self,
        transitions,
        strategy_name="",
        profile=None,
    ):
        """
        Analyze the complete transition history.
        """

        return self._aggregate(
            transitions,
            strategy_name,
            "FULL",
            profile,
        )

    def analyze_periods(
        self,
        transitions,
        strategy_name="",
        profile=None,
    ):
        """
        Analyze the configured historical periods.
        """

        results = []

        for period_name, definition in (
            ANALYSIS_PERIODS.items()
        ):

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
                    profile,
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
        profile,
    ):

        transitions = list(transitions)

        if not transitions:

            return TransitionAggregate(
                strategy=strategy_name,
                period=period_name,

                state_transitions=0,
                trades=0,

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

        records = []

        for transition in transitions:

            from_asset = self._asset_for_state(
                transition.from_state,
                profile,
            )

            to_asset = self._asset_for_state(
                transition.to_state,
                profile,
            )

            trade_occurred = (
                from_asset != to_asset
            )

            records.append(
                {
                    "date": transition.date,

                    "from_state":
                        transition.from_state,

                    "to_state":
                        transition.to_state,

                    "from_asset":
                        from_asset,

                    "to_asset":
                        to_asset,

                    "trade_occurred":
                        trade_occurred,

                    "whipsaw":
                        (
                            transition.whipsaw
                            if trade_occurred
                            else False
                        ),

                    "duration":
                        transition.duration_days,

                    "exit_timing":
                        self._exit_timing(
                            transition,
                            trade_occurred,
                        ),

                    "reentry_timing":
                        self._reentry_timing(
                            transition,
                            trade_occurred,
                        ),

                    "missed_upside":
                        self._missed_upside(
                            transition,
                            trade_occurred,
                        ),

                    "avoided_downside":
                        self._avoided_downside(
                            transition,
                            trade_occurred,
                        ),

                    "quality":
                        (
                            transition.transition_quality
                            if trade_occurred
                            else None
                        ),
                }
            )

        frame = pd.DataFrame(records)

        trades = frame[
            frame["trade_occurred"]
        ]

        exits = trades[
            trades["to_state"]
            == "DEFENSIVE"
        ]

        reentries = trades[
            (
                trades["from_state"]
                == "DEFENSIVE"
            )
            &
            (
                trades["to_state"]
                != "DEFENSIVE"
            )
        ]

        defensive = frame[
            frame["to_state"]
            == "DEFENSIVE"
        ]

        return TransitionAggregate(
            strategy=strategy_name,
            period=period_name,

            state_transitions=len(frame),

            trades=len(trades),

            whipsaws=int(
                trades["whipsaw"].sum()
            ),

            whipsaw_rate=self._rate(
                trades["whipsaw"]
            ),

            average_exit_timing=self._mean(
                exits["exit_timing"]
            ),

            median_exit_timing=self._median(
                exits["exit_timing"]
            ),

            average_reentry_timing=self._mean(
                reentries["reentry_timing"]
            ),

            median_reentry_timing=self._median(
                reentries["reentry_timing"]
            ),

            average_defensive_duration=self._mean(
                defensive["duration"]
            ),

            median_defensive_duration=self._median(
                defensive["duration"]
            ),

            average_missed_upside=self._mean(
                exits["missed_upside"]
            ),

            median_missed_upside=self._median(
                exits["missed_upside"]
            ),

            average_avoided_downside=self._mean(
                exits["avoided_downside"]
            ),

            median_avoided_downside=self._median(
                exits["avoided_downside"]
            ),

            average_transition_quality=self._mean(
                trades["quality"]
            ),
        )

    # ================================================================
    # STATE → ASSET MAPPING
    # ================================================================

    @staticmethod
    def _asset_for_state(
        state,
        profile,
    ):
        """
        Resolve the actual portfolio asset for a strategy state.

        Supports the profile structures currently used by MarketPilot,
        while deliberately avoiding assumptions about strategy names.
        """

        if profile is None:
            return state

        state = str(
            state
        ).upper()

        #
        # Common profile attributes.
        #

        if state == "AGGRESSIVE":

            value = getattr(
                profile,
                "aggressive_asset",
                None,
            )

            if value is not None:
                return str(value)

        if state == "MODERATE":

            value = getattr(
                profile,
                "moderate_asset",
                None,
            )

            if value is not None:
                return str(value)

        if state == "DEFENSIVE":

            #
            # Some profiles have a single defensive asset.
            #

            value = getattr(
                profile,
                "defensive_asset",
                None,
            )

            if value is not None:
                return str(value)

            #
            # Others use defensive_assets.
            #

            values = getattr(
                profile,
                "defensive_assets",
                None,
            )

            if values:

                return str(
                    values[0]
                )

            #
            # Cash defensive profiles.
            #

            value = getattr(
                profile,
                "cash_asset",
                None,
            )

            if value is not None:
                return str(value)

            value = getattr(
                profile,
                "defensive",
                None,
            )

            if value is not None:
                return str(value)

        #
        # Last-resort mapping. This should only be reached if a
        # profile doesn't expose the expected asset attributes.
        #

        return state

    # ================================================================
    # TRADE CLASSIFICATION
    # ================================================================

    @staticmethod
    def _exit_timing(
        transition,
        trade_occurred,
    ):

        if not trade_occurred:
            return None

        if (
            str(
                transition.to_state
            ).upper()
            != "DEFENSIVE"
        ):
            return None

        return getattr(
            transition,
            "exit_vs_previous_10d_high",
            None,
        )

    @staticmethod
    def _reentry_timing(
        transition,
        trade_occurred,
    ):

        if not trade_occurred:
            return None

        if (
            str(
                transition.from_state
            ).upper()
            != "DEFENSIVE"
        ):
            return None

        return getattr(
            transition,
            "entry_vs_10d_low",
            None,
        )

    @staticmethod
    def _missed_upside(
        transition,
        trade_occurred,
    ):

        if not trade_occurred:
            return None

        if (
            str(
                transition.to_state
            ).upper()
            != "DEFENSIVE"
        ):
            return None

        #
        # Prefer the explicit field if it exists.
        #

        value = getattr(
            transition,
            "missed_upside",
            None,
        )

        if value is not None:
            return value

        #
        # Backward compatibility with the existing analyzer.
        #

        return getattr(
            transition,
            "upside_captured",
            None,
        )

    @staticmethod
    def _avoided_downside(
        transition,
        trade_occurred,
    ):

        if not trade_occurred:
            return None

        if (
            str(
                transition.to_state
            ).upper()
            != "DEFENSIVE"
        ):
            return None

        value = getattr(
            transition,
            "downside_avoided",
            None,
        )

        if value is None:
            return None

        #
        # Report avoided downside as a positive number.
        #

        return max(
            0.0,
            -float(value),
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
    def _mean(values):

        if values is None:
            return None

        series = pd.Series(
            values
        ).dropna()

        if series.empty:
            return None

        return float(
            series.mean()
        )

    @staticmethod
    def _median(values):

        if values is None:
            return None

        series = pd.Series(
            values
        ).dropna()

        if series.empty:
            return None

        return float(
            series.median()
        )

    @staticmethod
    def _rate(values):

        if values is None:
            return None

        series = pd.Series(
            values
        ).dropna()

        if series.empty:
            return None

        return float(
            series.mean()
        )