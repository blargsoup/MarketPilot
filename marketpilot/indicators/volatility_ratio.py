"""
Volatility Ratio (VR)

Current realized volatility divided by its
252-day moving average.
"""

import pandas as pd

from .realized_volatility import realized_volatility


def volatility_ratio(
    close: pd.Series,
    short_window: int = 21,
    long_window: int = 252,
) -> pd.Series:
    """
    Calculate the Volatility Ratio (VR).

    VR = Current realized volatility /
         252-day average realized volatility

    A value above 1.0 means volatility is higher than its
    long-term average.
    """

    rv = realized_volatility(close, short_window)

    baseline = rv.rolling(long_window).mean()

    return rv / baseline