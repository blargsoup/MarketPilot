"""
Moving average indicators.
"""

import pandas as pd


def simple_moving_average(
    series: pd.Series,
    period: int,
) -> pd.Series:
    """
    Calculate a simple moving average.
    """

    return series.rolling(period).mean()