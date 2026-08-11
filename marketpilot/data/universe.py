"""
MarketPilot market universe.

Every asset known to the application is
defined here.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Asset:

    symbol: str

    name: str

    description: str

    category: str

    leverage: int = 1

    dashboard: bool = False

    dashboard_group: str = ""


MARKET_UNIVERSE = [

    #
    # NASDAQ
    #

    Asset(
        "QQQ",
        "Invesco QQQ Trust",
        "NASDAQ-100 ETF",
        "NASDAQ",
        1,
        True,
        "NASDAQ",
    ),

    Asset(
        "QLD",
        "ProShares Ultra QQQ",
        "NASDAQ-100 2x Leveraged",
        "NASDAQ",
        2,
        True,
        "NASDAQ",
    ),

    Asset(
        "TQQQ",
        "ProShares UltraPro QQQ",
        "NASDAQ-100 3x Leveraged",
        "NASDAQ",
        3,
        True,
        "NASDAQ",
    ),

    #
    # S&P 500
    #

    Asset(
        "SPY",
        "SPDR S&P 500",
        "S&P 500 ETF",
        "S&P500",
        1,
        True,
        "S&P 500",
    ),

    Asset(
        "SSO",
        "ProShares Ultra S&P500",
        "S&P 500 2x Leveraged",
        "S&P500",
        2,
        True,
        "S&P 500",
    ),

    Asset(
        "UPRO",
        "ProShares UltraPro S&P500",
        "S&P 500 3x Leveraged",
        "S&P500",
        3,
        True,
        "S&P 500",
    ),

    #
    # Semiconductor
    #

    Asset(
        "SMH",
        "VanEck Semiconductor",
        "Semiconductor ETF",
        "Technology",
        1,
        True,
        "Semiconductors",
    ),

    Asset(
        "USD",
        "ProShares Ultra Semiconductors",
        "Semiconductor 2x Leveraged",
        "Technology",
        2,
        True,
        "Semiconductors",
    ),

    Asset(
        "SOXL",
        "Direxion Semiconductor Bull",
        "Semiconductor 3x Leveraged",
        "Technology",
        3,
        True,
        "Semiconductors",
    ),

    #
    # Berkshire
    #

    Asset(
        "BRK-B",
        "Berkshire Hathaway",
        "Class B Shares",
        "Diversified",
        1,
        True,
        "Other",
    ),

    #
    # Factors
    #

    Asset(
        "AVUV",
        "Avantis US Small Cap Value",
        "US Small Cap Value",
        "Factor",
        1,
        True,
        "Factors",
    ),

    #
    # Broad Market
    #

    Asset(
        "VTI",
        "Vanguard Total Stock Market",
        "US Total Market",
        "Broad Market",
        1,
        True,
        "Broad Market",
    ),

    Asset(
        "RSP",
        "Invesco Equal Weight S&P500",
        "Equal Weight S&P500",
        "Broad Market",
        1,
        True,
        "Broad Market",
    ),

    #
    # International
    #

    Asset(
        "VXUS",
        "Vanguard Total International",
        "International Stocks",
        "International",
        1,
        True,
        "International",
    ),

    Asset(
        "VEA",
        "Vanguard Developed Markets",
        "Developed Markets",
        "International",
        1,
        True,
        "International",
    ),

    Asset(
        "VWO",
        "Vanguard Emerging Markets",
        "Emerging Markets",
        "International",
        1,
        True,
        "International",
    ),

    #
    # Bonds
    #

    Asset(
        "HYG",
        "iShares High Yield Bond",
        "High Yield Credit",
        "Credit",
        1,
    ),

    Asset(
        "LQD",
        "iShares Investment Grade Bond",
        "Investment Grade Credit",
        "Credit",
        1,
    ),

    Asset(
        "TLT",
        "iShares 20+ Treasury",
        "Long Treasury Bonds",
        "Bond",
        1,
    ),

    #
    # Cash
    #

    Asset(
        "TBILL",
        "3-Month U.S. Treasury Bills",
        "Synthetic Treasury Cash Equivalent",
        "Cash",
        1,
        False,
        "Cash",
    ),

    Asset(
        "SGOV",
        "iShares Treasury 0-3 Month",
        "Cash Equivalent",
        "Cash",
        1,
    ),

    Asset(
        "BIL",
        "SPDR Treasury Bill",
        "Cash Equivalent",
        "Cash",
        1,
    ),

    #
    # Defensive
    #

    Asset(
        "GLD",
        "SPDR Gold",
        "Physical Gold",
        "Commodity",
        1,
        True,
        "Defensive",
    ),

    Asset(
        "GDX",
        "VanEck Gold Miners",
        "Gold Miners",
        "Commodity",
        1,
        True,
        "Defensive",
    ),

    Asset(
        "XLU",
        "Utilities Select Sector",
        "Utilities",
        "Defensive",
        1,
        True,
        "Defensive",
    ),

    Asset(
        "XLE",
        "Energy Select Sector",
        "Energy",
        "Sector",
        1,
        True,
        "Defensive",
    ),

    #
    # Canada
    #

    Asset(
        "XIC.TO",
        "iShares Core S&P/TSX",
        "Canadian Broad Market",
        "Canada",
        1,
        True,
        "Canada",
    ),
]