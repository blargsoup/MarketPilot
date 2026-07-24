from enum import Enum


class PortfolioState(Enum):

    TQQQ = (
        "TQQQ",
        "TQQQ",
    )

    QLD = (
        "QLD",
        "QLD",
    )

    DEFENSIVE = (
        "DEFENSIVE",
        "TLT",
    )

    def __init__(
        self,
        label,
        asset,
    ):

        self.label = label
        self.asset = asset