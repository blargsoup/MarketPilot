"""
Signal and transition analytics.

Analyzes individual signal activations and state transitions
using the completed backtest history.

This module performs analysis only.
It does not write files or produce console output.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd


SIGNALS = (
    "rvol_over_qld",
    "vr_over_qld",
    "spy_breakdown",
    "credit_crisis",
    "donchian_break",
    "donchian_confirmed",
)


SIGNAL_LABELS = {
    "rvol_over_qld": "RVol > QLD",
    "vr_over_qld": "VR > QLD",
    "spy_breakdown": "SPY Breakdown",
    "credit_crisis": "Credit Crisis",
    "donchian_break": "Donchian Break",
    "donchian_confirmed": "Donchian Confirmed",
}


HORIZONS = (
    5,
    20,
    60,
    120,
)


class SignalAnalytics:

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        comparisons,
    ) -> tuple[
        pd.DataFrame,
        pd.DataFrame,
        pd.DataFrame,
    ]:
        """
        Analyze all supplied strategy comparisons.

        Returns:

            signal_events
            signal_summary
            transition_events
        """

        signal_frames = []
        transition_frames = []

        for comparison in comparisons:

            daily = self._build_daily_history(
                comparison
            )

            if daily.empty:
                continue

            signal_events = (
                self._analyze_signal_events(
                    daily,
                    comparison.name,
                )
            )

            transition_events = (
                self._analyze_transitions(
                    daily,
                    comparison.name,
                )
            )

            if not signal_events.empty:
                signal_frames.append(
                    signal_events
                )

            if not transition_events.empty:
                transition_frames.append(
                    transition_events
                )

        if signal_frames:

            signal_events = pd.concat(
                signal_frames,
                ignore_index=True,
            )

        else:

            signal_events = pd.DataFrame()

        if transition_frames:

            transition_events = pd.concat(
                transition_frames,
                ignore_index=True,
            )

        else:

            transition_events = pd.DataFrame()

        signal_summary = (
            self._build_signal_summary(
                signal_events
            )
        )

        return (
            signal_events,
            signal_summary,
            transition_events,
        )

    # ------------------------------------------------------------------
    # Daily reconstruction
    # ------------------------------------------------------------------

    def _build_daily_history(
        self,
        comparison,
    ):

        simulations = list(
            comparison.backtest.simulations
        )

        if not simulations:
            return pd.DataFrame()

        rows = []

        for simulation in simulations:

            date = pd.Timestamp(
                simulation.context.current_date
            ).normalize()

            signals = getattr(
                simulation,
                "signals",
                None,
            )

            strategy = getattr(
                simulation,
                "strategy",
                None,
            )

            portfolio_state = getattr(
                simulation,
                "portfolio_state",
                None,
            )

            state = self._state_name(
                portfolio_state,
                strategy,
            )

            asset = getattr(
                simulation,
                "symbol",
                None,
            )

            row = {
                "date": date,
                "equity": float(
                    simulation.equity
                ),
                "state": state,
                "asset": asset,
            }

            for signal in SIGNALS:

                row[signal] = self._signal_value(
                    signals,
                    signal,
                )

            row["rvol"] = self._signal_value(
                signals,
                "rvol",
            )

            row["vr"] = self._signal_value(
                signals,
                "vr",
            )

            row["spy_distance"] = self._signal_value(
                signals,
                "spy_distance",
            )

            row["credit"] = self._signal_value(
                signals,
                "credit",
            )

            row["transition_reasons"] = (
                self._transition_reasons(
                    strategy
                )
            )

            #
            # Pull the current close for every asset
            # available in this day's market view.
            #
            # MarketView is limited to the current date,
            # so this represents only information available
            # on that simulation day.
            #

            market = getattr(
                simulation,
                "market",
                None,
            )

            if market is not None:

                for symbol in market.keys():

                    try:

                        history = market[symbol]

                        if history.data.empty:
                            continue

                        close = (
                            history.data["Close"]
                            .iloc[-1]
                        )

                        row[
                            f"price_{symbol}"
                        ] = float(close)

                    except (
                        KeyError,
                        IndexError,
                        TypeError,
                    ):

                        continue

            rows.append(row)

        return (
            pd.DataFrame(rows)
            .sort_values("date")
            .drop_duplicates(
                subset=["date"],
                keep="last",
            )
            .reset_index(drop=True)
        )

    # ------------------------------------------------------------------
    # Signal events
    # ------------------------------------------------------------------

    def _analyze_signal_events(
        self,
        daily,
        strategy_name,
    ):

        rows = []

        for signal in SIGNALS:

            values = (
                daily[signal]
                .fillna(False)
                .astype(bool)
            )

            #
            # Rising edge only.
            #
            # We want the day a signal becomes active,
            # not every day it remains active.
            #

            activated = (
                values
                & ~values.shift(
                    1,
                    fill_value=False,
                )
            )

            indexes = daily.index[
                activated
            ]

            for index in indexes:

                row = daily.loc[index]

                event = {
                    "Strategy":
                        strategy_name,

                    "Date":
                        row["date"].date(),

                    "Signal":
                        SIGNAL_LABELS[
                            signal
                        ],

                    "State":
                        row["state"],

                    "Asset":
                        row["asset"],

                    "Equity":
                        row["equity"],

                    "RVol":
                        row["rvol"],

                    "VR":
                        row["vr"],

                    "SPY vs 200 SMA":
                        row["spy_distance"],

                    "Credit":
                        row["credit"],

                    "Transition Reasons":
                        row[
                            "transition_reasons"
                        ],
                }

                #
                # Forward behavior of the current
                # held asset.
                #

                asset = row["asset"]

                for horizon in HORIZONS:

                    event[
                        f"Asset Return +{horizon}d"
                    ] = self._forward_return(
                        daily,
                        index,
                        asset,
                        horizon,
                    )

                for horizon in (
                    20,
                    60,
                    120,
                ):

                    (
                        max_gain,
                        gain_days,
                    ) = self._forward_extreme(
                        daily,
                        index,
                        asset,
                        horizon,
                        maximum=True,
                    )

                    (
                        max_drawdown,
                        drawdown_days,
                    ) = self._forward_extreme(
                        daily,
                        index,
                        asset,
                        horizon,
                        maximum=False,
                    )

                    event[
                        f"Max Gain +{horizon}d"
                    ] = max_gain

                    event[
                        f"Days To Max Gain +{horizon}d"
                    ] = gain_days

                    event[
                        f"Max Drawdown +{horizon}d"
                    ] = max_drawdown

                    event[
                        f"Days To Max Drawdown +{horizon}d"
                    ] = drawdown_days

                rows.append(event)

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Transition analysis
    # ------------------------------------------------------------------

    def _analyze_transitions(
        self,
        daily,
        strategy_name,
    ):

        rows = []

        for index in daily.index:

            row = daily.loc[index]

            if not self._is_transition(
                daily,
                index,
            ):
                continue

            previous_state = (
                daily.loc[
                    index - 1,
                    "state",
                ]
            )

            current_state = row["state"]

            direction = self._transition_type(
                previous_state,
                current_state,
            )

            held_asset = (
                daily.loc[
                    index - 1,
                    "asset",
                ]
            )

            target_asset = row["asset"]

            event = {

                "Strategy":
                    strategy_name,

                "Date":
                    row["date"].date(),

                "Transition":
                    f"{previous_state} -> "
                    f"{current_state}",

                "Transition Type":
                    direction,

                "From State":
                    previous_state,

                "To State":
                    current_state,

                "Held Asset":
                    held_asset,

                "New Asset":
                    target_asset,

                "Equity":
                    row["equity"],

                "RVol":
                    row["rvol"],

                "VR":
                    row["vr"],

                "SPY vs 200 SMA":
                    row["spy_distance"],

                "Credit":
                    row["credit"],

                "RVol > QLD":
                    row["rvol_over_qld"],

                "VR > QLD":
                    row["vr_over_qld"],

                "SPY Breakdown":
                    row["spy_breakdown"],

                "Credit Crisis":
                    row["credit_crisis"],

                "Donchian Break":
                    row["donchian_break"],

                "Donchian Confirmed":
                    row["donchian_confirmed"],

                "Transition Reasons":
                    row["transition_reasons"],
            }

            #
            # How far had the held asset already moved
            # immediately before the transition?
            #

            for horizon in (
                5,
                20,
                60,
            ):

                event[
                    f"Held Asset Return -{horizon}d"
                ] = self._backward_return(
                    daily,
                    index,
                    held_asset,
                    horizon,
                )

            #
            # What happened after the transition?
            #

            for horizon in HORIZONS:

                event[
                    f"Held Asset Return +{horizon}d"
                ] = self._forward_return(
                    daily,
                    index,
                    held_asset,
                    horizon,
                )

                event[
                    f"New Asset Return +{horizon}d"
                ] = self._forward_return(
                    daily,
                    index,
                    target_asset,
                    horizon,
                )

            #
            # Maximum subsequent move in the held asset.
            #

            for horizon in (
                20,
                60,
                120,
            ):

                (
                    max_gain,
                    gain_days,
                ) = self._forward_extreme(
                    daily,
                    index,
                    held_asset,
                    horizon,
                    maximum=True,
                )

                (
                    max_drawdown,
                    drawdown_days,
                ) = self._forward_extreme(
                    daily,
                    index,
                    held_asset,
                    horizon,
                    maximum=False,
                )

                event[
                    f"Held Asset Max Gain +{horizon}d"
                ] = max_gain

                event[
                    f"Held Asset Days To Max Gain +{horizon}d"
                ] = gain_days

                event[
                    f"Held Asset Max Drawdown +{horizon}d"
                ] = max_drawdown

                event[
                    f"Held Asset Days To Max Drawdown +{horizon}d"
                ] = drawdown_days

            rows.append(event)

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Signal summary
    # ------------------------------------------------------------------

    @staticmethod
    def _build_signal_summary(
        events,
    ):

        if events.empty:
            return pd.DataFrame()

        rows = []

        for (
            strategy,
            signal,
        ), group in events.groupby(
            [
                "Strategy",
                "Signal",
            ]
        ):

            row = {

                "Strategy":
                    strategy,

                "Signal":
                    signal,

                "Events":
                    len(group),
            }

            for horizon in (
                5,
                20,
                60,
                120,
            ):

                column = (
                    f"Asset Return +{horizon}d"
                )

                if column not in group:
                    continue

                series = group[
                    column
                ].dropna()

                if series.empty:
                    continue

                row[
                    f"Average Return +{horizon}d"
                ] = series.mean()

                row[
                    f"Median Return +{horizon}d"
                ] = series.median()

                row[
                    f"Positive Rate +{horizon}d"
                ] = (
                    series > 0
                ).mean()

            rows.append(row)

        return pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _state_name(
        portfolio_state,
        strategy,
    ):

        for value in (
            portfolio_state,
            getattr(
                strategy,
                "new_state",
                None,
            ),
        ):

            if value is None:
                continue

            name = getattr(
                value,
                "name",
                None,
            )

            if name:
                return name

        return None

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
        strategy,
    ):

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

    @staticmethod
    def _is_transition(
        daily,
        index,
    ):

        if index == 0:
            return False

        return (
            daily.loc[
                index,
                "state",
            ]
            !=
            daily.loc[
                index - 1,
                "state",
            ]
        )

    @staticmethod
    def _transition_type(
        previous,
        current,
    ):

        if (
            previous == "DEFENSIVE"
            and current != "DEFENSIVE"
        ):
            return "REENTRY"

        if (
            previous != "DEFENSIVE"
            and current == "DEFENSIVE"
        ):
            return "EXIT"

        return "ROTATION"

    @staticmethod
    def _price_column(
        daily,
        symbol,
    ):

        if not symbol:
            return None

        column = f"price_{symbol}"

        if column not in daily.columns:
            return None

        return column

    def _forward_return(
        self,
        daily,
        index,
        symbol,
        horizon,
    ):

        column = self._price_column(
            daily,
            symbol,
        )

        if column is None:
            return None

        future_index = (
            index + horizon
        )

        if future_index >= len(daily):
            return None

        start = daily.loc[
            index,
            column,
        ]

        end = daily.loc[
            future_index,
            column,
        ]

        if (
            pd.isna(start)
            or pd.isna(end)
            or start == 0
        ):
            return None

        return (
            end / start
        ) - 1.0

    def _backward_return(
        self,
        daily,
        index,
        symbol,
        horizon,
    ):

        column = self._price_column(
            daily,
            symbol,
        )

        if column is None:
            return None

        previous_index = (
            index - horizon
        )

        if previous_index < 0:
            return None

        start = daily.loc[
            previous_index,
            column,
        ]

        end = daily.loc[
            index,
            column,
        ]

        if (
            pd.isna(start)
            or pd.isna(end)
            or start == 0
        ):
            return None

        return (
            end / start
        ) - 1.0

    def _forward_extreme(
        self,
        daily,
        index,
        symbol,
        horizon,
        maximum,
    ):

        column = self._price_column(
            daily,
            symbol,
        )

        if column is None:
            return None, None

        end_index = min(
            index + horizon,
            len(daily) - 1,
        )

        start_price = daily.loc[
            index,
            column,
        ]

        if pd.isna(start_price):
            return None, None

        window = daily.loc[
            index:end_index,
            column,
        ].dropna()

        if window.empty:
            return None, None

        returns = (
            window / start_price
        ) - 1.0

        if maximum:

            value = returns.max()

        else:

            value = returns.min()

        date_index = returns[
            returns == value
        ].index[0]

        days = (
            date_index - index
        )

        return (
            float(value),
            int(days),
        )