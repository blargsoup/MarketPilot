"""
Canonical trading calendar used throughout MarketPilot.
"""

from __future__ import annotations


class MarketCalendar:

    def __init__(self, dates):
        self._dates = dates.sort_values()

    @classmethod
    def from_market(
        cls,
        market,
        required_symbols=None,
    ):
        """
        Build a trading calendar.

        If required_symbols is supplied, only those assets determine
        the calendar. This prevents unrelated assets in the global
        market universe from shortening the backtest.
        """

        if required_symbols is None:
            required_symbols = list(
                market.keys()
            )

        common_dates = None

        for symbol in required_symbols:

            if symbol not in market:
                raise KeyError(
                    f"Required market symbol "
                    f"{symbol} is missing."
                )

            history = market[symbol]

            dates = history.data.index

            if common_dates is None:
                common_dates = dates

            else:
                common_dates = (
                    common_dates.intersection(
                        dates
                    )
                )

        if common_dates is None or len(common_dates) == 0:
            raise ValueError(
                "No common trading dates found "
                "for required market symbols."
            )

        return cls(common_dates)

    def __len__(self):
        return len(self._dates)

    def __iter__(self):
        return iter(self._dates)

    def __getitem__(self, index):
        return self._dates[index]

    @property
    def dates(self):
        return self._dates

    @property
    def first_date(self):
        return self._dates[0]

    @property
    def last_date(self):
        return self._dates[-1]

    def contains(self, date):
        return date in self._dates

    def index_of(self, date):
        return self._dates.get_loc(date)