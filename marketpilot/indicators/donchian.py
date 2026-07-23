"""
Donchian channel indicator.

Returns True whenever price makes
a new N-day closing low.
"""

import pandas as pd


def donchian_low(
    close: pd.Series,
    window: int = 40,
) -> pd.Series:

    previous_low = (
        close.shift(1)
        .rolling(window)
        .min()
    )

    return close <= previous_low