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
    ):

        #
        # Build a calendar that contains
        # only dates present in every
        # market history.
        #

        common_dates = None

        for history in market.values():

            dates = history.data.index

            if common_dates is None:

                common_dates = dates

            else:

                common_dates = common_dates.intersection(
                    dates
                )

        return cls(common_dates)

    def __len__(self):

        return len(self._dates)

    def __iter__(self):

        return iter(self._dates)

    def __getitem__(
        self,
        index,
    ):

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