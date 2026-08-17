"""
Strategy Profiles

A StrategyProfile contains every tunable parameter required by a strategy.

Strategies themselves contain no ETF names and no hard-coded thresholds.

Profiles allow the exact same strategy to operate on NASDAQ,
Semiconductors, SPY, or any future market.
"""

from dataclasses import dataclass

from .state import PortfolioState


@dataclass(frozen=True)
class StrategyProfile:

    print("Loaded StrategyProfile from:", __file__)

    ####################################################################
    # Display
    ####################################################################

    name: str

    ####################################################################
    # Market assets
    ####################################################################

    signal_asset: str

    trend_asset: str

    aggressive_asset: str

    moderate_asset: str

    ####################################################################
    # Defensive universe
    ####################################################################

    defensive_assets: tuple[str, ...]

    cash_asset: str

    ####################################################################
    # Realized Volatility thresholds
    ####################################################################

    rvol_qld: float = 0.18

    rvol_defensive: float = 0.36

    rvol_recovery: float = 0.14

    rvol_defensive_recovery: float = 0.25

    ####################################################################
    # Volatility Ratio thresholds
    ####################################################################

    vr_qld: float = 1.25

    vr_defensive: float = 1.40

    vr_recovery: float = 0.90

    vr_defensive_recovery: float = 1.10

    ####################################################################
    # Trend thresholds
    ####################################################################

    spy_breakdown: float = -0.03

    spy_recovery: float = -0.015

    spy_clear: float = 0.03

    ####################################################################
    # Credit stress
    ####################################################################

    credit_threshold: float = -0.04

    ####################################################################
    # Donchian confirmation / recovery
    ####################################################################

    # Minimum realized volatility required before a Donchian break
    # becomes a valid defensive exit.
    donchian_rvol: float = 0.20

    # Require a 3% bounce from the trailing low before allowing
    # re-entry into QLD.
    donchian_recovery: float = 0.03

    # Safety valve. If the bounce never comes, allow re-entry after
    # this many trading days.
    donchian_timeout: int = 20

    ####################################################################
    # Defensive asset filter
    ####################################################################

    defensive_max_extension: float = 0.15

    ####################################################################
    # Convenience helpers
    ####################################################################

    def asset_for_state(

        self,

        state: PortfolioState,

    ):

        if state == PortfolioState.AGGRESSIVE:

            return self.aggressive_asset

        if state == PortfolioState.MODERATE:

            return self.moderate_asset

        return self.cash_asset


##############################################################################
# NASDAQ
##############################################################################

NASDAQ_PROFILE = StrategyProfile(

    name="NASDAQ",

    signal_asset="QQQ",

    trend_asset="SPY",

    aggressive_asset="TQQQ",

    moderate_asset="QLD",

    defensive_assets=(

        "TLT",
        "GLD",
        "XLU",
        "XLE",

    ),

    cash_asset="CASH",

)


##############################################################################
# Semiconductors
##############################################################################

SEMICONDUCTOR_PROFILE = StrategyProfile(

    name="Semiconductors",

    signal_asset="SMH",

    trend_asset="SPY",

    aggressive_asset="SOXL",

    moderate_asset="USD",

    defensive_assets=(

        "TLT",
        "GLD",
        "XLU",
        "XLE",

    ),

    cash_asset="CASH",

)


##############################################################################
# S&P 500
##############################################################################

SP500_PROFILE = StrategyProfile(

    name="S&P 500",

    signal_asset="SPY",

    trend_asset="SPY",

    aggressive_asset="UPRO",

    moderate_asset="SSO",

    defensive_assets=(

        "TLT",
        "GLD",
        "XLU",
        "XLE",

    ),

    cash_asset="CASH",

)

##############################################################################
# NASDAQ - Cash Defensive
##############################################################################

NASDAQ_CASH_PROFILE = StrategyProfile(

    name="NASDAQ Cash Defensive",

    signal_asset="QQQ",

    trend_asset="SPY",

    aggressive_asset="TQQQ",

    moderate_asset="QLD",

    defensive_assets=(),

    cash_asset="CASH",

)


##############################################################################
# NASDAQ - QQQ Moderate
##############################################################################

NASDAQ_QQQ_PROFILE = StrategyProfile(

    name="NASDAQ QQQ Moderate",

    signal_asset="QQQ",

    trend_asset="SPY",

    aggressive_asset="TQQQ",

    moderate_asset="QQQ",

    defensive_assets=(

        "TLT",
        "GLD",
        "XLU",
        "XLE",

    ),

    cash_asset="CASH",

)