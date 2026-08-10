"""
Volatility Ratio

A-RVol V3 definition:

    Current 15-day realized volatility
    ----------------------------------
    Trailing 252-day average of 15-day
    realized volatility

The result is dimensionless.

Examples:

    0.80 = current volatility is 20% below its
           trailing yearly average

    1.00 = current volatility is at its
           trailing yearly average

    1.25 = current volatility is 25% above
           its trailing yearly average
"""

import pandas as pd

from .realized_volatility import realized_volatility


def volatility_ratio(
    close: pd.Series,
    rvol_window: int = 15,
    average_window: int = 252,
) -> pd.Series:

    """
    Calculate the A-RVol volatility ratio.

    VR = current 15-day realized volatility /
         trailing 252-day average of 15-day
         realized volatility.
    """

    rvol = realized_volatility(
        close,
        window=rvol_window,
    )

    trailing_average = (
        rvol
        .rolling(average_window)
        .mean()
    )

    return (
        rvol
        / trailing_average
    )