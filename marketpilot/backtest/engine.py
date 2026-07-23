"""
Generic backtesting engine.

Initially this simply walks
through history.

Trading logic will be added
later.
"""

from .context import BacktestContext


class BacktestEngine:

    def __init__(self):

        pass

    def run(
        self,
        market,
    ):

        #
        # Use QQQ as the master calendar.
        #

        qqq = market["QQQ"]

        dates = qqq.close.index

        contexts = []

        for index, date in enumerate(dates):

            context = BacktestContext(

                current_date=date,

                current_index=index,

                total_days=len(dates),

            )

            contexts.append(
                context
            )

        return contexts