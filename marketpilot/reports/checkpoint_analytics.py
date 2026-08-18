"""
Checkpoint analytics engine.

Builds reusable daily and checkpoint-level diagnostics from
BacktestResult simulation history.

This module contains analytical logic only. It does not write CSV
files and does not produce console output.

The resulting data is intended to support:

    • Historical checkpoint analysis
    • Strategy comparison
    • Drawdown analysis
    • State/exposure analysis
    • Future UI reporting
    • Future strategy optimization
"""

from dataclasses import dataclass
from typing import Any

import pandas as pd


CHECKPOINTS = [
    ("2000-03-27", "Dot-com peak"),
    ("2002-10-04", "Dot-com max drawdown"),
    ("2007-10-31", "Pre-GFC peak"),
    ("2008-11-20", "GFC drawdown #1"),
    ("2009-03-09", "GFC maximum drawdown"),
    ("2021-11-19", "Pre-2022 peak"),
    ("2022-12-28", "2022 drawdown"),
    ("2024-12-16", "Pre-tariff peak"),
    ("2025-04-08", "Tariff drawdown"),
    ("2025-10-29", "Pre-Iran-war peak"),
    ("2026-03-30", "Iran-war drawdown"),
    ("2026-06-02", "Latest/current peak"),
]


@dataclass
class DailyDiagnostic:
    """
    Analytical snapshot for one trading day.
    """

    date: pd.Timestamp
    equity: float

    peak_equity: float
    drawdown: float

    state: str | None
    asset: str | None

    rvol: float | None
    vr: float | None
    spy_distance: float | None
    credit: float | None

    rvol_over_qld: bool | None
    vr_over_qld: bool | None
    spy_breakdown: bool | None
    credit_crisis: bool | None
    donchian_break: bool | None
    donchian_confirmed: bool | None

    state_changed: bool | None
    transition_reasons: str


class CheckpointAnalytics:
    """
    Converts backtest simulation history into reusable analytics.

    The class deliberately knows nothing about CSV files.
    """

    # ------------------------------------------------------------------
    # Generic helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _date(value) -> pd.Timestamp:
        return pd.Timestamp(value).normalize()

    @staticmethod
    def _state(simulation) -> str | None:

        portfolio_state = getattr(
            simulation,
            "portfolio_state",
            None,
        )

        if portfolio_state is not None:

            name = getattr(
                portfolio_state,
                "name",
                None,
            )

            if name is not None:
                return name

        strategy = getattr(
            simulation,
            "strategy",
            None,
        )

        if strategy is not None:

            state = getattr(
                strategy,
                "new_state",
                None,
            )

            if state is not None:

                name = getattr(
                    state,
                    "name",
                    None,
                )

                if name is not None:
                    return name

        return None

    @staticmethod
    def _asset(simulation) -> str | None:

        symbol = getattr(
            simulation,
            "symbol",
            None,
        )

        if symbol:
            return symbol

        strategy = getattr(
            simulation,
            "strategy",
            None,
        )

        if strategy is not None:

            for attribute in (
                "asset",
                "selected_asset",
            ):

                value = getattr(
                    strategy,
                    attribute,
                    None,
                )

                if value:
                    return value

        return None

    @staticmethod
    def _signals(simulation):

        return getattr(
            simulation,
            "signals",
            None,
        )

    @staticmethod
    def _signal_value(
        signals,
        name,
    ):

        if signals is None:
            return None

        return getattr(
            signals,
            name,
            None,
        )

    @staticmethod
    def _transition_reasons(
        simulation,
    ):

        strategy = getattr(
            simulation,
            "strategy",
            None,
        )

        if strategy is None:
            return ""

        reasons = getattr(
            strategy,
            "reasons",
            None,
        )

        if not reasons:
            return ""

        return " | ".join(
            str(reason)
            for reason in reasons
        )

    # ------------------------------------------------------------------
    # Build daily history
    # ------------------------------------------------------------------

    def build_daily_history(
        self,
        backtest,
    ) -> pd.DataFrame:
        """
        Build one analytical row for every simulation day.

        This is the core reusable dataset.

        Running peak and drawdown are calculated here once so that
        checkpoint reports and future UI/optimizer code do not need
        to repeatedly reconstruct them.
        """

        simulations = list(
            backtest.simulations
        )

        if not simulations:
            return pd.DataFrame()

        rows = []

        peak_equity = 0.0

        for simulation in simulations:

            date = self._date(
                simulation.context.current_date
            )

            equity = float(
                simulation.equity
            )

            if equity > peak_equity:
                peak_equity = equity

            if peak_equity > 0:

                drawdown = (
                    equity / peak_equity
                ) - 1.0

            else:

                drawdown = 0.0

            signals = self._signals(
                simulation
            )

            rows.append({

                "date": date,

                "equity": equity,

                "peak_equity":
                    peak_equity,

                "drawdown":
                    drawdown,

                "state":
                    self._state(
                        simulation
                    ),

                "asset":
                    self._asset(
                        simulation
                    ),

                "rvol":
                    self._signal_value(
                        signals,
                        "rvol",
                    ),

                "vr":
                    self._signal_value(
                        signals,
                        "vr",
                    ),

                "spy_distance":
                    self._signal_value(
                        signals,
                        "spy_distance",
                    ),

                "credit":
                    self._signal_value(
                        signals,
                        "credit",
                    ),

                "rvol_over_qld":
                    self._signal_value(
                        signals,
                        "rvol_over_qld",
                    ),

                "vr_over_qld":
                    self._signal_value(
                        signals,
                        "vr_over_qld",
                    ),

                "spy_breakdown":
                    self._signal_value(
                        signals,
                        "spy_breakdown",
                    ),

                "credit_crisis":
                    self._signal_value(
                        signals,
                        "credit_crisis",
                    ),

                "donchian_break":
                    self._signal_value(
                        signals,
                        "donchian_break",
                    ),

                "donchian_confirmed":
                    self._signal_value(
                        signals,
                        "donchian_confirmed",
                    ),

                "state_changed":
                    getattr(
                        getattr(
                            simulation,
                            "strategy",
                            None,
                        ),
                        "changed",
                        None,
                    ),

                "transition_reasons":
                    self._transition_reasons(
                        simulation
                    ),
            })

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Checkpoint date matching
    # ------------------------------------------------------------------

    @staticmethod
    def _actual_checkpoint_date(
        dates: pd.DatetimeIndex,
        requested_date: pd.Timestamp,
    ) -> pd.Timestamp | None:
        """
        Find the requested date or the most recent trading date
        before it.
        """

        if requested_date in dates:
            return requested_date

        eligible = dates[
            dates <= requested_date
        ]

        if len(eligible) == 0:
            return None

        return eligible[-1]

    # ------------------------------------------------------------------
    # Period analytics
    # ------------------------------------------------------------------

    @staticmethod
    def _period_rows(
        daily: pd.DataFrame,
        previous_date: pd.Timestamp | None,
        current_date: pd.Timestamp,
    ) -> pd.DataFrame:

        if previous_date is None:

            return daily[
                daily["date"] <= current_date
            ]

        return daily[
            (daily["date"] > previous_date)
            &
            (daily["date"] <= current_date)
        ]

    @staticmethod
    def _state_days(
        period: pd.DataFrame,
        state: str,
    ) -> int:

        if period.empty:
            return 0

        return int(
            (
                period["state"]
                == state
            ).sum()
        )

    @staticmethod
    def _state_changes(
        period: pd.DataFrame,
    ) -> int:

        if period.empty:
            return 0

        return int(
            period["state_changed"]
            .fillna(False)
            .sum()
        )

    @staticmethod
    def _max_period_drawdown(
        period: pd.DataFrame,
    ) -> float | None:

        if period.empty:
            return None

        return float(
            period["drawdown"].min()
        )

    @staticmethod
    def _period_peak(
        period: pd.DataFrame,
        previous_peak: float,
    ) -> float:

        if period.empty:
            return previous_peak

        return max(
            previous_peak,
            float(
                period["equity"].max()
            ),
        )

    # ------------------------------------------------------------------
    # Recovery analysis
    # ------------------------------------------------------------------

    @staticmethod
    def _recovery_analysis(
        daily: pd.DataFrame,
        current_date: pd.Timestamp,
    ) -> dict[str, Any]:

        history = daily[
            daily["date"] <= current_date
        ].copy()

        if history.empty:
            return {
                "days_underwater": 0,
                "recovery_days": None,
                "recovery_date": None,
            }

        #
        # Most recent all-time peak.
        #

        peak_equity = (
            history["peak_equity"].iloc[-1]
        )

        current_equity = (
            history["equity"].iloc[-1]
        )

        if current_equity >= peak_equity:

            return {
                "days_underwater": 0,
                "recovery_days": None,
                "recovery_date": None,
            }

        #
        # Find the date of the peak.
        #

        peak_rows = history[
            history["equity"]
            == history["peak_equity"]
        ]

        if peak_rows.empty:
            return {
                "days_underwater": 0,
                "recovery_days": None,
                "recovery_date": None,
            }

        peak_date = peak_rows[
            "date"
        ].iloc[-1]

        underwater = history[
            history["date"] > peak_date
        ]

        return {
            "days_underwater":
                int(len(underwater)),

            "recovery_days":
                None,

            "recovery_date":
                None,
        }

    # ------------------------------------------------------------------
    # Checkpoint analysis
    # ------------------------------------------------------------------

    def analyze_strategy(
        self,
        comparison,
    ) -> pd.DataFrame:
        """
        Produce detailed checkpoint rows for one strategy.
        """

        daily = self.build_daily_history(
            comparison.backtest
        )

        if daily.empty:
            return pd.DataFrame()

        dates = pd.DatetimeIndex(
            daily["date"]
        )

        #
        # Fast lookup by date.
        #

        daily_by_date = (
            daily
            .drop_duplicates(
                subset=["date"],
                keep="last",
            )
            .set_index("date")
        )

        rows = []

        previous_date = None
        previous_equity = None
        previous_peak = 0.0

        for date_string, event in CHECKPOINTS:

            requested_date = self._date(
                date_string
            )

            actual_date = (
                self._actual_checkpoint_date(
                    dates,
                    requested_date,
                )
            )

            if actual_date is None:
                continue

            checkpoint = daily_by_date.loc[
                actual_date
            ]

            equity = float(
                checkpoint["equity"]
            )

            #
            # Return since previous checkpoint.
            #

            if (
                previous_equity is not None
                and previous_equity != 0
            ):

                checkpoint_return = (
                    equity / previous_equity
                ) - 1.0

            else:

                checkpoint_return = None

            #
            # Period from previous checkpoint
            # through this checkpoint.
            #

            period = self._period_rows(
                daily,
                previous_date,
                actual_date,
            )

            #
            # Period peak.
            #

            period_peak = self._period_peak(
                period,
                previous_peak,
            )

            #
            # Overall drawdown at checkpoint.
            #

            if period_peak > 0:

                drawdown_from_peak = (
                    equity / period_peak
                ) - 1.0

            else:

                drawdown_from_peak = 0.0

            #
            # Recovery state.
            #

            recovery = (
                self._recovery_analysis(
                    daily,
                    actual_date,
                )
            )

            rows.append({

                "Date":
                    date_string,

                "Actual Trading Date":
                    actual_date.date(),

                "Event":
                    event,

                "Strategy":
                    comparison.name,

                "State":
                    checkpoint["state"],

                "Asset":
                    checkpoint["asset"],

                "Equity":
                    equity,

                "Checkpoint Return":
                    checkpoint_return,

                "Drawdown From Peak":
                    drawdown_from_peak,

                "Period Peak Equity":
                    period_peak,

                "Max Period Drawdown":
                    self._max_period_drawdown(
                        period
                    ),

                "Days Aggressive":
                    self._state_days(
                        period,
                        "AGGRESSIVE",
                    ),

                "Days Moderate":
                    self._state_days(
                        period,
                        "MODERATE",
                    ),

                "Days Defensive":
                    self._state_days(
                        period,
                        "DEFENSIVE",
                    ),

                "State Changes":
                    self._state_changes(
                        period
                    ),

                "Days Underwater":
                    recovery[
                        "days_underwater"
                    ],

                "Recovery Days":
                    recovery[
                        "recovery_days"
                    ],

                "Recovery Date":
                    recovery[
                        "recovery_date"
                    ],

                #
                # Signals at checkpoint.
                #

                "RVol":
                    checkpoint["rvol"],

                "VR":
                    checkpoint["vr"],

                "SPY vs 200 SMA":
                    checkpoint["spy_distance"],

                "Credit":
                    checkpoint["credit"],

                "RVol > QLD":
                    checkpoint["rvol_over_qld"],

                "VR > QLD":
                    checkpoint["vr_over_qld"],

                "SPY Breakdown":
                    checkpoint["spy_breakdown"],

                "Credit Crisis":
                    checkpoint["credit_crisis"],

                "Donchian Break":
                    checkpoint["donchian_break"],

                "Donchian Confirmed":
                    checkpoint[
                        "donchian_confirmed"
                    ],

                "State Changed":
                    checkpoint[
                        "state_changed"
                    ],

                "Transition Reasons":
                    checkpoint[
                        "transition_reasons"
                    ],
            })

            previous_date = actual_date
            previous_equity = equity
            previous_peak = period_peak

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # All strategies
    # ------------------------------------------------------------------

    def analyze(
        self,
        comparisons,
    ) -> pd.DataFrame:
        """
        Analyze every strategy supplied by the comparison runner.

        No strategy names are hard-coded here.
        """

        frames = []

        for comparison in comparisons:

            frame = self.analyze_strategy(
                comparison
            )

            if not frame.empty:
                frames.append(frame)

        if not frames:
            return pd.DataFrame()

        return pd.concat(
            frames,
            ignore_index=True,
        )