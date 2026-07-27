"""
Maps portfolio states to ETFs.

Different strategies may eventually
provide different mappings.
"""

from .state import PortfolioState


ETF_MAP = {

    PortfolioState.TQQQ: "TQQQ",

    PortfolioState.QLD: "QLD",

    PortfolioState.DEFENSIVE: "TLT",

}