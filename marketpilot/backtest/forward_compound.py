from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import pandas as pd


@dataclass
class ForwardCompoundResult:
    equity: pd.Series
    daily_returns: pd.Series
    states: pd.Series

    starting_value: float
    ending_value: float
    total_return: float
    cagr: float
    max_drawdown: float

    aggressive_days: int
    moderate_days: int
    defensive_days: int


class ForwardCompounder:
    """
    Compounds a strategy forward through time using daily asset returns.

    The strategy state determines which asset is held on each day.

    Important:
        The state is assumed to be determined using information available
        at the end of the previous trading day. The return for the current
        day is therefore earned by the asset selected by the previous state.
    """

    def __init__(
        self,
        starting_value: float = 100_000.0,
        state_assets: Optional[Dict[str, str]] = None,
    ) -> None:

        self.starting_value = starting_value

        self.state_assets = state_assets or {
            "AGGRESSIVE": "TQQQ",
            "MODERATE": "QLD",
            "DEFENSIVE": "TBILL",
        }

    def run(
        self,
        market: Dict[str, pd.DataFrame],
        states: pd.Series,
        price_column: str = "Adj Close",
    ) -> ForwardCompoundResult:

        if states.empty:
            raise ValueError("Cannot compound an empty state series.")

        returns = {}

        for state, symbol in self.state_assets.items():

            if symbol not in market:
                raise ValueError(
                    f"Required asset '{symbol}' for state '{state}' "
                    "was not found in market data."
                )

            prices = market[symbol][price_column].astype(float)

            returns[state] = prices.pct_change()

        returns_df = pd.DataFrame(returns)

        states = states.copy()
        states.index = pd.to_datetime(states.index)

        returns_df.index = pd.to_datetime(returns_df.index)

        combined = pd.DataFrame(index=states.index)

        combined["state"] = states

        for state in self.state_assets:
            combined[state] = returns_df[state].reindex(combined.index)

        # ------------------------------------------------------------
        # IMPORTANT:
        #
        # The state at day T determines the asset held for day T+1.
        # Shift the state by one trading day before selecting returns.
        # ------------------------------------------------------------

        held_state = combined["state"].shift(1)

        selected_returns = pd.Series(
            0.0,
            index=combined.index,
            dtype=float,
        )

        for state in self.state_assets:
            mask = held_state == state
            selected_returns.loc[mask] = combined.loc[mask, state]

        # The first day has no prior state.
        selected_returns.iloc[0] = 0.0

        # Do not allow missing market returns to silently become zero.
        missing = selected_returns.isna()

        if missing.any():

            bad_dates = selected_returns.index[missing]

            raise ValueError(
                "Missing asset returns encountered during forward "
                f"compounding. First missing date: {bad_dates[0]}"
            )

        # ------------------------------------------------------------
        # Compound portfolio value
        # ------------------------------------------------------------

        equity = self.starting_value * (1.0 + selected_returns).cumprod()

        # ------------------------------------------------------------
        # Drawdown
        # ------------------------------------------------------------

        rolling_peak = equity.cummax()

        drawdown = equity / rolling_peak - 1.0

        max_drawdown = float(drawdown.min())

        # ------------------------------------------------------------
        # CAGR
        # ------------------------------------------------------------

        days = (equity.index[-1] - equity.index[0]).days

        if days > 0 and equity.iloc[-1] > 0:
            years = days / 365.25

            cagr = (
                equity.iloc[-1] / self.starting_value
            ) ** (1.0 / years) - 1.0

        else:
            cagr = 0.0

        # ------------------------------------------------------------
        # State exposure
        # ------------------------------------------------------------

        valid_states = held_state.dropna()

        aggressive_days = int(
            (valid_states == "AGGRESSIVE").sum()
        )

        moderate_days = int(
            (valid_states == "MODERATE").sum()
        )

        defensive_days = int(
            (valid_states == "DEFENSIVE").sum()
        )

        return ForwardCompoundResult(
            equity=equity,
            daily_returns=selected_returns,
            states=held_state,

            starting_value=self.starting_value,
            ending_value=float(equity.iloc[-1]),

            total_return=(
                float(equity.iloc[-1] / self.starting_value - 1.0)
            ),

            cagr=cagr,
            max_drawdown=max_drawdown,

            aggressive_days=aggressive_days,
            moderate_days=moderate_days,
            defensive_days=defensive_days,
        )