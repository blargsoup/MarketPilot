"""
Canonical trading calendar used throughout MarketPilot.

The backtest calendar is based only on assets required by the
strategy being tested. Optional assets and benchmark-only assets
must not shorten the historical backtest period.
"""

from __future__ import annotations


class MarketCalendar:

    def __init__(
        self,
        dates,
    ):

        self._dates = dates.sort_values()

    @classmethod
    def from_market(
        cls,
        market,
        required_symbols=None,
    ):
        """
        Build the trading calendar from the required market assets.

        If required_symbols is supplied, only those histories determine
        the calendar. This prevents optional or young assets such as
        SGOV, AVUV, etc. from limiting the historical backtest period.

        If required_symbols is omitted, preserve the previous behavior
        of using the intersection of every market history.
        """

        #
        # Backward-compatible behavior.
        #
        if required_symbols is None:

            required_symbols = list(market.keys())

        #
        # Validate that every required asset exists.
        #
        missing_symbols = [
            symbol
            for symbol in required_symbols
            if symbol not in market
        ]

        if missing_symbols:

            raise ValueError(
                "Missing required market data for: "
                + ", ".join(missing_symbols)
            )

        #
        # Build the calendar from only the required assets.
        #
        common_dates = None

        for symbol in required_symbols:

            history = market[symbol]

            dates = history.data.index

            if common_dates is None:

                common_dates = dates

            else:

                common_dates = common_dates.intersection(
                    dates
                )

        if common_dates is None:

            return cls([])

        return cls(common_dates)

    def __len__(
        self,
    ):

        return len(self._dates)

    def __iter__(
        self,
    ):

        return iter(self._dates)

    def __getitem__(
        self,
        index,
    ):

        return self._dates[index]

    @property
    def dates(
        self,
    ):

        return self._dates

    @property
    def first_date(
        self,
    ):

        return self._dates[0]

    @property
    def last_date(
        self,
    ):

        return self._dates[-1]

    def contains(
        self,
        date,
    ):

        return date in self._dates

    def index_of(
        self,
        date,
    ):

        return self._dates.get_loc(date)