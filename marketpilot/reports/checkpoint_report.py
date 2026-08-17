"""
Historical checkpoint reporting.

Produces a CSV containing strategy state, portfolio value,
drawdown, market indicators, and benchmark information at
important historical dates.
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

    def generate(
        self,
        market,
        backtest_results,
    ):

        rows = []

        #
        # Build lookup by date.
        #

        simulations = {
            simulation.context.current_date.normalize():
                simulation
            for simulation in backtest_results.simulations
        }

        #
        # Build equity lookup.
        #

        equity = {
            point.date.normalize(): point
            for point in backtest_results.equity_curve
        }

        #
        # Build high-water-mark lookup.
        #

        high_water = 0.0
        drawdown_lookup = {}

        for point in backtest_results.equity_curve:

            value = point.equity

            if value > high_water:
                high_water = value

            if high_water > 0:
                drawdown = (
                    value / high_water
                ) - 1.0

            else:
                drawdown = 0.0

            drawdown_lookup[
                point.date.normalize()
            ] = drawdown

        #
        # Process checkpoints.
        #

        for date_string, event in CHECKPOINTS:

            date = pd.Timestamp(date_string)

            #
            # Find exact simulation date.
            #

            simulation = simulations.get(date)

            #
            # Some checkpoints may fall on weekends or holidays.
            #
            # If there isn't an exact trading day, use the most
            # recent available simulation on or before the date.
            #

            if simulation is None:

                available = [
                    d
                    for d in simulations
                    if d <= date
                ]

                if not available:
                    continue

                actual_date = max(available)

                simulation = simulations[
                    actual_date
                ]

            else:

                actual_date = date

            #
            # Portfolio value.
            #

            equity_point = equity.get(actual_date)

            if equity_point is not None:

                portfolio_value = equity_point.equity

            else:

                portfolio_value = None

            #
            # Strategy drawdown.
            #

            strategy_drawdown = drawdown_lookup.get(
                actual_date
            )

            #
            # Signals.
            #

            signals = simulation.signals

            #
            # Strategy state.
            #

            strategy_result = simulation.strategy

            #
            # Defensive asset.
            #

            defensive_asset = ""

            if hasattr(
                simulation,
                "defensive",
            ):

                defensive_asset = (
                    simulation.defensive.symbol
                )

            #
            # Market prices.
            #

            def latest_close(symbol):

                if symbol not in market:
                    return None

                history = market[symbol]

                data = history.data

                available = data.loc[
                    data.index <= actual_date
                ]

                if available.empty:
                    return None

                return float(
                    available["Close"].iloc[-1]
                )

            #
            # Add row.
            #

            rows.append({

                "Date":
                    date_string,

                "Actual Trading Date":
                    actual_date.date(),

                "Event":
                    event,

                #
                # Strategy
                #

                "Strategy State":
                    strategy_result.new_state.name,

                "Strategy Portfolio":
                    portfolio_value,

                "Strategy Drawdown":
                    strategy_drawdown,

                "Defensive Asset":
                    defensive_asset,

                #
                # Market prices
                #

                "QQQ Close":
                    latest_close("QQQ"),

                "TQQQ Synthetic Close":
                    latest_close("TQQQ"),

                "QLD Synthetic Close":
                    latest_close("QLD"),

                #
                # Indicators
                #

                "RVol":
                    signals.rvol,

                "VR":
                    signals.vr,

                "SPY vs 200 SMA":
                    signals.spy_distance,

                "Credit":
                    signals.credit,

                #
                # Boolean signals
                #

                "RVol > QLD":
                    signals.rvol_over_qld,

                "VR > QLD":
                    signals.vr_over_qld,

                "SPY Breakdown":
                    signals.spy_breakdown,

                "Credit Crisis":
                    signals.credit_crisis,

                "Donchian Break":
                    signals.donchian_break,

                "Donchian Confirmed":
                    signals.donchian_confirmed,

                #
                # Transition
                #

                "State Changed":
                    strategy_result.changed,

                "Transition Reasons":
                    " | ".join(
                        strategy_result.reasons
                    ),

            })

        #
        # Create DataFrame.
        #

        dataframe = pd.DataFrame(rows)

        #
        # Ensure output directory exists.
        #

        self.output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        #
        # Write CSV.
        #

        dataframe.to_csv(
            self.output_path,
            index=False,
        )

        return self.output_path