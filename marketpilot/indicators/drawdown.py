"""
Drawdown calculations.

Provides the current drawdown of an asset from its
highest closing price over the previous two years.
"""

from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class DrawdownResult:

    current_price: float

    peak_price: float

    drawdown: float

    def __mul__(self, other):
        """
        Allow existing report code such as:

            dd * 100

        to continue working.
        """

        return self.drawdown * other

    def __rmul__(self, other):
        return self.drawdown * other


def drawdown_from_2y_high(history) -> DrawdownResult:

    """
    Calculate the current drawdown from the highest closing
    price over the previous two years.

    Returns:
        DrawdownResult containing:

        current_price
        peak_price
        drawdown
    """

    if history is None:
        return DrawdownResult(
            current_price=0.0,
            peak_price=0.0,
            drawdown=0.0,
        )

    df = history.data.copy()

    if df.empty:
        return DrawdownResult(
            current_price=0.0,
            peak_price=0.0,
            drawdown=0.0,
        )

    # Make sure the index is datetime.
    df.index = pd.to_datetime(df.index)

    # Sort oldest -> newest.
    df = df.sort_index()

    # Last 730 calendar days.
    end_date = df.index[-1]

    start_date = (
        end_date - pd.Timedelta(days=730)
    )

    window = df.loc[
        df.index >= start_date
    ]

    if window.empty:
        window = df

    close = window["Close"].dropna()

    if close.empty:
        return DrawdownResult(
            current_price=0.0,
            peak_price=0.0,
            drawdown=0.0,
        )

    current_price = float(
        close.iloc[-1]
    )

    peak_price = float(
        close.max()
    )

    drawdown = (
        current_price / peak_price
    ) - 1.0

    return DrawdownResult(
        current_price=current_price,
        peak_price=peak_price,
        drawdown=drawdown,
    )