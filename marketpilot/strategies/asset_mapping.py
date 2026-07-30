"""
Maps portfolio states to ETFs for a given strategy profile.
"""

from .state import PortfolioState


def asset_for_state(
    profile,
    state,
):
    if state == PortfolioState.AGGRESSIVE:
        return profile.aggressive_asset

    if state == PortfolioState.MODERATE:
        return profile.moderate_asset

    raise ValueError(f"No asset mapping for {state}")