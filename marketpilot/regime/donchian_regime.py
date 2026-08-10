"""
Donchian recovery regime.

Tracks the temporary recovery state after a Donchian-triggered
defensive exit.

The regime itself contains no A-RVol strategy logic.

Behavior:

    EOD trigger day
        QQQ hits 40-day low AND RVol >= 20%
        QLD -> DEF

    Following days
        Track QQQ's trailing 5-day low.

    Recovery
        QQQ closes >= 3% above the trailing 5-day low

    Safety valve
        Recovery is also permitted after 20 trading days.

The trigger-day close is retained as historical context, but the
recovery window is evaluated using the actual trailing five trading
days available after the defensive exit.
"""

from dataclasses import dataclass, field
from collections import deque


@dataclass
class DonchianRegime:

    ####################################################################
    # Configuration
    ####################################################################

    trailing_days: int = 5

    recovery_threshold: float = 0.03

    timeout_days: int = 20

    ####################################################################
    # Persistent state
    ####################################################################

    active: bool = False

    start_index: int = -1

    current_index: int = -1

    #
    # QQQ closes observed while the recovery regime is active.
    #
    # The trigger-day close is intentionally NOT inserted here.
    #
    # The first value is therefore the first trading day's close
    # after the defensive exit.
    #

    closes: deque = field(
        default_factory=deque
    )

    ####################################################################
    # Lifecycle
    ####################################################################

    def activate(
        self,
        index: int,
    ):
        """
        Activate the Donchian recovery regime.

        The trigger-day close caused the defensive exit and is therefore
        not part of the recovery-day five-day window.

        The following trading day is recovery day 1.
        """

        self.active = True

        self.start_index = index

        self.current_index = index

        self.closes.clear()

    def clear(self):
        """
        End the Donchian recovery regime.
        """

        self.active = False

        self.start_index = -1

        self.current_index = -1

        self.closes.clear()

    ####################################################################
    # Daily update
    ####################################################################

    def update(
        self,
        index: int,
        close: float,
    ):
        """
        Record a recovery-day close.

        This should be called once per trading day AFTER the
        Donchian trigger day.
        """

        if not self.active:

            return

        #
        # Do not accidentally process the trigger day.
        #

        if index <= self.start_index:

            return

        self.current_index = index

        self.closes.append(close)

        #
        # Maintain the trailing five-trading-day window.
        #

        while len(self.closes) > self.trailing_days:

            self.closes.popleft()

    ####################################################################
    # Information
    ####################################################################

    @property
    def days_active(self):
        """
        Number of trading days elapsed since the Donchian trigger.
        """

        if not self.active:

            return 0

        return (
            self.current_index
            - self.start_index
        )

    @property
    def lowest_close(self):
        """
        Lowest QQQ closing price in the current trailing five-day
        recovery window.
        """

        if not self.closes:

            return None

        return min(self.closes)

    ####################################################################
    # Recovery
    ####################################################################

    def recovery_percent(
        self,
        close: float,
    ):
        """
        Calculate QQQ's recovery from the trailing five-day low.

        Returns:

            0.0
                if the regime is inactive or there is no recovery
                window yet.

            Otherwise:
                close / trailing_5d_low - 1
        """

        if (
            not self.active
            or
            self.lowest_close is None
        ):

            return 0.0

        return (
            close
            / self.lowest_close
        ) - 1

    @property
    def recovered(self):
        """
        True when QQQ has recovered at least the configured
        percentage from its trailing five-day low.
        """

        if not self.active:

            return False

        if self.lowest_close is None:

            return False

        return (
            self.recovery_percent(
                self.current_close
            )
            >= self.recovery_threshold
        )

    @property
    def timeout(self):
        """
        True once the configured safety-valve period has elapsed.
        """

        if not self.active:

            return False

        return (
            self.days_active
            >= self.timeout_days
        )

    @property
    def current_close(self):
        """
        Most recently recorded recovery-day close.
        """

        if not self.closes:

            return None

        return self.closes[-1]