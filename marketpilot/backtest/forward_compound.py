from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

import logging
import pandas as pd

logger = logging.getLogger(__name__)


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

    benchmark_equity: Dict[str, pd.Series]
    benchmark_ending_values: Dict[str, float]
    benchmark_total_returns: Dict[str, float]


class ForwardCompounder:
    """
    Compounds a strategy forward through time using daily asset returns.

    All assets:
    The daily economic return is calculated from the historical
    economic value supplied by the market data provider.

    Synthetic leveraged ETFs:
        TQQQ, QLD, etc. are supplied by SyntheticDataProvider as
        authoritative historical datasets and are treated exactly like
        normal assets.

    No leveraged ETF returns are reconstructed here.

    The strategy state determines which asset is held on each day.

    Important:
        The state at day T is assumed to be determined using information
        available at the end of day T.

        Therefore the state at day T determines the asset held during
        day T+1.

    This one-day shift prevents look-ahead bias.
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

    # ------------------------------------------------------------------
    # Return calculation
    # ------------------------------------------------------------------

    def _get_asset_returns(
        self,
        symbol: str,
        market,
        price_column: str,
    ) -> pd.Series:
        """
        Return the daily economic return series for an asset.

        The market data provider is authoritative.

        Synthetic leveraged ETFs such as TQQQ and QLD are supplied by
        SyntheticDataProvider as historical datasets, so they are treated
        exactly like any other asset here.

        No leverage reconstruction is performed.
        """

        if symbol not in market:
            raise ValueError(
                f"Required asset '{symbol}' was not found "
                f"in market data."
            )

        history = market[symbol]

        #
        # Use the economic value series when one is available.
        #
        # Synthetic leveraged datasets may contain NAV, which represents
        # the economic investment value independently of share-price
        # denomination and splits.
        #

        if "NAV" in history.data.columns:

            prices = (
                history.data["NAV"]
                .astype(float)
            )

        else:

            if price_column not in history.data.columns:
                raise ValueError(
                    f"Asset '{symbol}' does not contain "
                    f"required price column '{price_column}'."
                )

            prices = (
                history.data[price_column]
                .astype(float)
            )

        prices.index = pd.to_datetime(
            prices.index
        )

        prices = prices.sort_index()

        if prices.empty:
            raise ValueError(
                f"Asset '{symbol}' contains no price data."
            )

        returns = prices.pct_change()

        logger.info(
            "Using supplied historical return series: %s",
            symbol,
        )

        return returns

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(
        self,
        market,
        states: pd.Series,
        price_column: str = "Close",
    ) -> ForwardCompoundResult:

        if states.empty:
            raise ValueError(
                "Cannot compound an empty state series."
            )

        # --------------------------------------------------------------
        # Build daily return series for each state asset.
        # --------------------------------------------------------------

        returns = {}

        for state, symbol in self.state_assets.items():

            returns[state] = self._get_asset_returns(
                symbol=symbol,
                market=market,
                price_column=price_column,
            )

        # --------------------------------------------------------------
        # Diagnostics
        # --------------------------------------------------------------

        for state, symbol in self.state_assets.items():

            asset_returns = returns[state].dropna()

            logger.info(
                "Forward return diagnostics: %s (%s)",
                state,
                symbol,
            )

            logger.info(
                "    First return : %.6f%%",
                asset_returns.iloc[0] * 100,
            )

            logger.info(
                "    Worst return : %.6f%%",
                asset_returns.min() * 100,
            )

            logger.info(
                "    Best return  : %.6f%%",
                asset_returns.max() * 100,
            )

            logger.info(
                "    Mean return  : %.6f%%",
                asset_returns.mean() * 100,
            )

            logger.info(
                "    Return rows  : %d",
                len(asset_returns),
            )

        # --------------------------------------------------------------
        # Normalize indexes.
        # --------------------------------------------------------------

        states = states.copy()
        states.index = pd.to_datetime(states.index)

        returns_df = pd.DataFrame(returns)
        returns_df.index = pd.to_datetime(
            returns_df.index
        )

        # --------------------------------------------------------------
        # Align strategy states and asset returns.
        # --------------------------------------------------------------

        combined = pd.DataFrame(
            index=states.index
        )

        combined["state"] = states

        for state in self.state_assets:

            combined[state] = (
                returns_df[state]
                .reindex(combined.index)
            )

        # --------------------------------------------------------------
        # IMPORTANT:
        #
        # The state at day T determines the asset held for day T+1.
        #
        # Shift the state by one trading day before selecting returns.
        # --------------------------------------------------------------

        held_state = combined["state"].shift(1)

        selected_returns = pd.Series(
            0.0,
            index=combined.index,
            dtype=float,
        )

        for state in self.state_assets:

            mask = held_state == state

            selected_returns.loc[mask] = (
                combined.loc[mask, state]
            )

        # The first day has no prior state.
        selected_returns.iloc[0] = 0.0

        # --------------------------------------------------------------
        # Do not allow missing market returns to silently become zero.
        # --------------------------------------------------------------

        missing = selected_returns.isna()

        if missing.any():

            bad_dates = selected_returns.index[
                missing
            ]

            raise ValueError(
                "Missing asset returns encountered during "
                "forward compounding. "
                f"First missing date: {bad_dates[0]}"
            )

        # --------------------------------------------------------------
        # Compound portfolio value.
        # --------------------------------------------------------------

        equity = (
            self.starting_value
            * (1.0 + selected_returns).cumprod()
        )

        # --------------------------------------------------------------
        # Forward-return buy-and-hold benchmarks.
        #
        # These use the exact same daily return series as the strategy,
        # but remain invested in one asset for the entire simulation.
        # --------------------------------------------------------------

        benchmark_equity: Dict[str, pd.Series] = {}
        benchmark_ending_values: Dict[str, float] = {}
        benchmark_total_returns: Dict[str, float] = {}

        for state_name, return_series in returns.items():
            benchmark_returns = (
                return_series
                .reindex(selected_returns.index)
            )

            # The first day has no prior-day return.
            benchmark_returns = benchmark_returns.fillna(0.0)

            benchmark_curve = (
                self.starting_value
                * (1.0 + benchmark_returns).cumprod()
            )

            benchmark_equity[state_name] = benchmark_curve

            benchmark_ending_values[state_name] = float(
                benchmark_curve.iloc[-1]
            )

            benchmark_total_returns[state_name] = float(
                benchmark_curve.iloc[-1]
                / self.starting_value
                - 1.0
            )


        # --------------------------------------------------------------
        # Drawdown.
        # --------------------------------------------------------------

        rolling_peak = equity.cummax()

        drawdown = (
            equity / rolling_peak
            - 1.0
        )

        max_drawdown = float(
            drawdown.min()
        )

        # --------------------------------------------------------------
        # CAGR.
        # --------------------------------------------------------------

        days = (
            equity.index[-1]
            - equity.index[0]
        ).days

        if (
            days > 0
            and equity.iloc[-1] > 0
        ):

            years = days / 365.25

            cagr = (
                equity.iloc[-1]
                / self.starting_value
            ) ** (1.0 / years) - 1.0

        else:
            cagr = 0.0

        # --------------------------------------------------------------
        # State exposure.
        # --------------------------------------------------------------

        valid_states = held_state.dropna()

        aggressive_days = int(
            (
                valid_states
                == "AGGRESSIVE"
            ).sum()
        )

        moderate_days = int(
            (
                valid_states
                == "MODERATE"
            ).sum()
        )

        defensive_days = int(
            (
                valid_states
                == "DEFENSIVE"
            ).sum()
        )

        # --------------------------------------------------------------
        # Result.
        # --------------------------------------------------------------

        return ForwardCompoundResult(
            equity=equity,
            daily_returns=selected_returns,
            states=held_state,
            starting_value=self.starting_value,
            ending_value=float(
                equity.iloc[-1]
            ),
            total_return=float(
                equity.iloc[-1]
                / self.starting_value
                - 1.0
            ),
            cagr=cagr,
            max_drawdown=max_drawdown,
            aggressive_days=aggressive_days,
            moderate_days=moderate_days,
            defensive_days=defensive_days,
            benchmark_equity=benchmark_equity,
            benchmark_ending_values=benchmark_ending_values,
            benchmark_total_returns=benchmark_total_returns,
        )