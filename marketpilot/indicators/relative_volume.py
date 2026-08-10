"""
Relative Volume Indicator

Relative Volume compares today's trading volume to the average
daily trading volume over a configurable lookback period.

A value of:

    1.00

means today's volume equals the average.

1.25 means volume is 25% above normal.

0.80 means volume is 20% below normal.

This is the Relative Volume used by the A-RVol strategy.

It is NOT the same as Realized Volatility.
"""

from __future__ import annotations

import pandas as pd


def relative_volume(
    volume: pd.Series,
    window: int = 21,
) -> pd.Series:
    """
    Calculate Relative Volume.

    Returns
    -------
    pandas.Series

        Relative volume ratio.

        Example:

            1.20

        means today's volume is 20% above the rolling
        average.
    """

    average = volume.rolling(window).mean()

    return volume / average