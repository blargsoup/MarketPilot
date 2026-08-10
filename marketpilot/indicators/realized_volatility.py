"""
Realized volatility indicator.
"""

import numpy as np
import pandas as pd


TRADING_DAYS = 252


def realized_volatility(
    close: pd.Series,
    window: int = 15,
) -> pd.Series:
    """
    Annualized realized volatility.

    Returned as a decimal.
    Example:
        0.18 = 18%
    """

    returns = np.log(close / close.shift(1))

    return (
        returns
        .rolling(window)
        .std()
        * np.sqrt(TRADING_DAYS)
    )