"""
Historical checkpoint reporting.

Produces a CSV comparing important historical dates across
multiple strategy variants and buy-and-hold benchmarks.
"""

from pathlib import Path

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


class CheckpointReport:

    def __init__(
        self,
        output_path="output/checkpoints.csv",
    ):

        self.output_path = Path(output_path)

    @staticmethod
    def _date_lookup(
        equity_curve,
    ):

        return {
            point.date.normalize(): point
            for point in equity_curve
        }

    @staticmethod
    def _drawdown_lookup(
        equity_curve,
    ):

        high_water = 0.0

        drawdowns = {}

        for point in equity_curve:

            equity = point.equity

            if equity > high_water:
                high_water = equity

            if high_water > 0:

                drawdown = (
                    equity / high_water
                ) - 1.0

            else:

                drawdown = 0.0

            drawdowns[
                point.date.normalize()
            ] = drawdown

        return drawdowns

    @staticmethod
    def _simulation_lookup(
        backtest,
    ):

        return {
            simulation.context.current_date.normalize():
                simulation
            for simulation in backtest.simulations
        }

    @staticmethod
    def _find_checkpoint(
        lookup,
        date,
    ):

        #
        # Exact trading day.
        #

        if date in lookup:

            return date

        #
        # Weekend / holiday.
        #
        # Use the most recent available trading day.
        #

        available = [
            actual_date
            for actual_date in lookup
            if actual_date <= date
        ]

        if not available:

            return None

        return max(available)

    @staticmethod
    def _latest_close(
        market,
        symbol,
        date,
    ):

        if symbol not in market:

            return None

        history = market[symbol]

        data = history.data

        available = data.loc[
            data.index <= date
        ]

        if available.empty:

            return None

        return float(
            available["Close"].iloc[-1]
        )

    def _strategy_rows(
        self,
        market,
        comparison,
    ):

        backtest = comparison.backtest

        simulations = (
            self._simulation_lookup(
                backtest
            )
        )

        drawdowns = (
            self._drawdown_lookup(
                backtest.equity_curve
            )
        )

        rows = []

        for date_string, event in CHECKPOINTS:

            requested_date = pd.Timestamp(
                date_string
            )

            actual_date = self._find_checkpoint(
                simulations,
                requested_date,
            )

            if actual_date is None:

                continue

            simulation = simulations[
                actual_date
            ]

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
                    simulation.portfolio_state.name,

                "Asset":
                    simulation.symbol,

                "Portfolio":
                    simulation.equity,

                "Drawdown":
                    drawdowns.get(
                        actual_date
                    ),

                #
                # Indicators
                #

                "RVol":
                    simulation.signals.rvol,

                "VR":
                    simulation.signals.vr,

                "SPY vs 200 SMA":
                    simulation.signals.spy_distance,

                "Credit":
                    simulation.signals.credit,

                #
                # Boolean signals
                #

                "RVol > QLD":
                    simulation.signals.rvol_over_qld,

                "VR > QLD":
                    simulation.signals.vr_over_qld,

                "SPY Breakdown":
                    simulation.signals.spy_breakdown,

                "Credit Crisis":
                    simulation.signals.credit_crisis,

                "Donchian Break":
                    simulation.signals.donchian_break,

                "Donchian Confirmed":
                    simulation.signals.donchian_confirmed,

                #
                # Transition
                #

                "State Changed":
                    simulation.strategy.changed,

                "Transition Reasons":
                    " | ".join(
                        simulation.strategy.reasons
                    ),

            })

        return rows

    def _benchmark_rows(
        self,
        market,
    ):

        rows = []

        #
        # Buy-and-hold benchmark assets.
        #
        # These are informational only.
        #

        benchmark_symbols = [
            "TQQQ",
            "QLD",
            "QQQ",
        ]

        for date_string, event in CHECKPOINTS:

            requested_date = pd.Timestamp(
                date_string
            )

            row = {

                "Date":
                    date_string,

                "Actual Trading Date":
                    None,

                "Event":
                    event,

                "Strategy":
                    "Buy & Hold",

                "State":
                    None,

                "Asset":
                    None,

                "Portfolio":
                    None,

                "Drawdown":
                    None,

                "RVol":
                    None,

                "VR":
                    None,

                "SPY vs 200 SMA":
                    None,

                "Credit":
                    None,

                "RVol > QLD":
                    None,

                "VR > QLD":
                    None,

                "SPY Breakdown":
                    None,

                "Credit Crisis":
                    None,

                "Donchian Break":
                    None,

                "Donchian Confirmed":
                    None,

                "State Changed":
                    None,

                "Transition Reasons":
                    None,

            }

            #
            # Keep the benchmark prices available as columns.
            #

            for symbol in benchmark_symbols:

                row[
                    f"{symbol} Close"
                ] = self._latest_close(
                    market,
                    symbol,
                    requested_date,
                )

            rows.append(row)

        return rows

    def generate(
        self,
        market,
        strategy_comparisons,
    ):

        rows = []

        #
        # Strategy comparison rows.
        #

        for comparison in strategy_comparisons:

            rows.extend(
                self._strategy_rows(
                    market,
                    comparison,
                )
            )

        #
        # Benchmark rows.
        #

        rows.extend(
            self._benchmark_rows(
                market,
            )
        )

        dataframe = pd.DataFrame(
            rows
        )

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        dataframe.to_csv(
            self.output_path,
            index=False,
        )

        return self.output_path