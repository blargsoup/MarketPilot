"""
CSV reporting for signal and transition analytics.

Builds signal events from the daily SimulationResult history
produced by the backtest engine.
"""

from pathlib import Path


class SignalReport:

    def __init__(
        self,
        output_dir="output",
    ):
        self.output_dir = Path(output_dir)

    def generate(
        self,
        comparisons,
        market,
    ):
        from marketpilot.reports.signal_analytics import (
            SignalAnalytics,
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        all_signal_events = []

        #
        # Build signal events from each completed strategy
        # backtest.
        #
        for comparison in comparisons:

            simulations = getattr(
                comparison.backtest,
                "simulations",
                [],
            )

            if not simulations:
                continue

            events = self._build_events(
                comparison,
                simulations,
                market,
            )

            all_signal_events.extend(
                events
            )

        #
        # Run the new analytics engine.
        #
        analytics = SignalAnalytics(
            all_signal_events
        )

        #
        # Analyze all events.
        #
        signal_events = analytics.analyze()

        #
        # Aggregate by signal / transition reason.
        #
        signal_summary = analytics.summarize(
            signal_events
        )

        #
        # Output paths.
        #
        signal_events_path = (
            self.output_dir
            / "signal_events.csv"
        )

        signal_summary_path = (
            self.output_dir
            / "signal_summary.csv"
        )

        transition_path = (
            self.output_dir
            / "transition_analytics.csv"
        )

        #
        # Write detailed signal events.
        #
        analytics.write_attribution(
            signal_events,
            signal_events_path,
        )

        #
        # Write aggregate signal summary.
        #
        analytics.write_summary(
            signal_summary,
            signal_summary_path,
        )

        #
        # Transition analytics.
        #
        # The attribution rows already contain transition
        # boundaries, timing classifications, whipsaw state,
        # etc. Keep a dedicated copy for downstream analysis.
        #
        analytics.write_attribution(
            signal_events,
            transition_path,
        )

        return {
            "signal_events": signal_events_path,
            "signal_summary": signal_summary_path,
            "transition_analytics": transition_path,
        }

    # ==================================================================
    # Event construction
    # ==================================================================

    def _build_events(
        self,
        comparison,
        simulations,
        market,
    ):
        """
        Convert daily SimulationResult objects into signal events.

        A signal event is recorded when one of the strategy's boolean
        signals becomes active.

        We use rising-edge detection so a signal that remains TRUE for
        twenty consecutive days does not become twenty separate events.
        """

        events = []

        previous_signals = {}

        strategy_name = comparison.name

        for index, simulation in enumerate(simulations):

            signals = simulation.signals

            date = simulation.context.current_date

            state = self._state_name(
                simulation.portfolio_state
            )

            signal_values = {
                "RVol >18%":
                    getattr(
                        signals,
                        "rvol_over_qld",
                        False,
                    ),

                "VR >1.25":
                    getattr(
                        signals,
                        "vr_over_qld",
                        False,
                    ),

                "SPY Breakdown":
                    getattr(
                        signals,
                        "spy_breakdown",
                        False,
                    ),

                "Credit Crisis":
                    getattr(
                        signals,
                        "credit_crisis",
                        False,
                    ),

                "Donchian Break":
                    getattr(
                        signals,
                        "donchian_break",
                        False,
                    ),

                "Donchian+RVol":
                    getattr(
                        signals,
                        "donchian_confirmed",
                        False,
                    ),
            }

            for signal_name, active in signal_values.items():

                previous = previous_signals.get(
                    signal_name,
                    False,
                )

                if not active or previous:
                    continue

                events.append(
                    {
                        "Strategy": strategy_name,
                        "Date": date,
                        "Signal": signal_name,
                        "State": state,
                        "Asset": simulation.symbol,
                        "Equity": simulation.equity,

                        "RVol": getattr(
                            signals,
                            "rvol",
                            None,
                        ),

                        "VR": getattr(
                            signals,
                            "vr",
                            None,
                        ),

                        "SPY vs 200 SMA":
                            getattr(
                                signals,
                                "spy_distance",
                                None,
                            ),

                        "Credit":
                            getattr(
                                signals,
                                "credit",
                                None,
                            ),

                        "Transition Reasons":
                            self._transition_reasons(
                                simulation
                            ),
                    }
                )

                self._add_forward_metrics(
                    events[-1],
                    simulations,
                    index,
                    market,
                )

            previous_signals = signal_values

        return events

    def _add_forward_metrics(
        self,
        event,
        simulations,
        index,
        market,
    ):
        """
        Calculate forward performance from the signal date.

        Uses the full historical market supplied to generate(), rather
        than the point-in-time MarketView stored inside SimulationResult.

        Forward windows are measured in trading days.
        """

        asset = event["Asset"]

        base_date = simulations[
            index
        ].context.current_date

        base_price = self._historical_close(
            market,
            asset,
            base_date,
        )

        if base_price is None:
            return

        horizons = (
            5,
            10,
            20,
            60,
            120,
        )

        for horizon in horizons:

            future = simulations[
                index + 1:
                index + horizon + 1
            ]

            if len(future) < horizon:
                continue

            prices = []

            for simulation in future:

                date = (
                    simulation.context.current_date
                )

                price = self._historical_close(
                    market,
                    asset,
                    date,
                )

                if price is not None:
                    prices.append(
                        (
                            simulation,
                            price,
                        )
                    )

            if len(prices) < horizon:
                continue

            final_price = prices[-1][1]

            event[
                f"Asset Return +{horizon}d"
            ] = (
                final_price
                / base_price
                - 1.0
            )

            max_gain = None
            max_gain_day = None

            max_drawdown = None
            max_drawdown_day = None

            for day_number, (
                simulation,
                price,
            ) in enumerate(
                prices,
                start=1,
            ):

                return_value = (
                    price
                    / base_price
                    - 1.0
                )

                if (
                    max_gain is None
                    or return_value > max_gain
                ):
                    max_gain = return_value
                    max_gain_day = day_number

                if (
                    max_drawdown is None
                    or return_value < max_drawdown
                ):
                    max_drawdown = return_value
                    max_drawdown_day = day_number

            event[
                f"Max Gain +{horizon}d"
            ] = max_gain

            event[
                f"Days To Max Gain +{horizon}d"
            ] = max_gain_day

            event[
                f"Max Drawdown +{horizon}d"
            ] = max_drawdown

            event[
                f"Days To Max Drawdown +{horizon}d"
            ] = max_drawdown_day


    def _historical_close(
        self,
        market,
        symbol,
        date,
    ):
        """
        Return the actual historical close for a symbol/date.
        """

        try:

            history = market[symbol]

            data = history.data

            if date not in data.index:
                return None

            return float(
                data.loc[
                    date,
                    "Close",
                ]
            )

        except (
            KeyError,
            AttributeError,
            TypeError,
            ValueError,
        ):

            return None




    # ==================================================================
    # Helpers
    # ==================================================================

    @staticmethod
    def _state_name(
        state,
    ):
        if state is None:
            return ""

        return getattr(
            state,
            "name",
            str(state),
        )

    @staticmethod
    def _transition_reasons(
        simulation,
    ):
        """
        Extract the reasons from the strategy decision.

        StrategyResult.reasons is normally a list of strings.
        """

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

        if isinstance(
            reasons,
            (list, tuple),
        ):
            return " | ".join(
                str(reason)
                for reason in reasons
            )

        return str(reasons)