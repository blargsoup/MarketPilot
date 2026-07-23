"""
Credit stress indicator.

Uses the ratio of HYG / LQD.

A falling ratio means high-yield
bonds are underperforming investment
grade bonds, indicating increasing
credit stress.
"""

import pandas as pd


def credit_stress(
    hyg: pd.Series,
    lqd: pd.Series,
    window: int = 20,
) -> pd.Series:

    ratio = hyg / lqd

    return (
        ratio.pct_change(window)
        * 100
    )