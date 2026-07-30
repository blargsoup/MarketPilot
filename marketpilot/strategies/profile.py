"""
Strategy Profiles

A profile defines which ETFs correspond to the three portfolio
risk levels for a particular strategy.

The strategy itself never refers to specific ETF symbols.
Instead it asks the profile which asset represents:

    • Aggressive
    • Moderate
    • Defensive signal source

Examples

NASDAQ

    Aggressive : TQQQ
    Moderate   : QLD
    Signals    : QQQ

Semiconductors

    Aggressive : SOXL
    Moderate   : USD
    Signals    : SMH

S&P500

    Aggressive : UPRO
    Moderate   : SSO
    Signals    : SPY
"""

from dataclasses import dataclass

from .state import PortfolioState


@dataclass(frozen=True)
class StrategyProfile:

    #
    # Display name
    #

    name: str

    #
    # ETF used for indicators
    #

    signal_asset: str

    #
    # ETF used in aggressive mode
    #

    aggressive_asset: str

    #
    # ETF used in moderate mode
    #

    moderate_asset: str

    ####################################################################
    # Helpers
    ####################################################################

    def asset_for_state(
        self,
        state: PortfolioState,
    ) -> str:

        if state == PortfolioState.AGGRESSIVE:
            return self.aggressive_asset

        if state == PortfolioState.MODERATE:
            return self.moderate_asset

        raise ValueError(
            "DEFENSIVE assets are chosen dynamically."
        )


########################################################################
# Built-in Profiles
########################################################################

NASDAQ_PROFILE = StrategyProfile(

    name="NASDAQ",

    signal_asset="QQQ",

    aggressive_asset="TQQQ",

    moderate_asset="QLD",

)

SEMICONDUCTOR_PROFILE = StrategyProfile(

    name="Semiconductors",

    signal_asset="SMH",

    aggressive_asset="SOXL",

    moderate_asset="USD",

)

SP500_PROFILE = StrategyProfile(

    name="S&P 500",

    signal_asset="SPY",

    aggressive_asset="UPRO",

    moderate_asset="SSO",

)