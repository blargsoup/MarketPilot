"""
Daily dashboard report.
"""
from marketpilot.indicators.drawdown import drawdown_from_2y_high
from marketpilot.data import MARKET_UNIVERSE

class DashboardReport:

    def __init__(self, profile):

        self.profile = profile

    def display(
        self,
        logger,
        market,
        signals,
        strategy,
        defensive,
        profile,
    ):

        qqq = market["QQQ"]

        logger.info("")
        logger.info("=" * 60)
        logger.info("TODAY'S MARKET")
        logger.info("=" * 60)

        #
        # Determine current holding
        #

        if strategy.new_state.name == "AGGRESSIVE":

            holding = profile.aggressive_asset

        elif strategy.new_state.name == "MODERATE":

            holding = profile.moderate_asset

        else:

            holding = defensive.symbol

        logger.info("")
        logger.info("Portfolio")
        logger.info("------------------------------")

        logger.info(
            "%-15s : %s",
            "State",
            strategy.new_state.name,
        )

        logger.info(
            "%-15s : %s",
            "Holding",
            holding,
        )

        logger.info(
            "%-15s : %s",
            "Recommendation",
            "TRADE" if strategy.changed else "HOLD",
        )

        if strategy.changed:

            #
            # Determine the asset we are leaving
            #

            if strategy.current_state.name == "AGGRESSIVE":

                from_asset = profile.aggressive_asset

            elif strategy.current_state.name == "MODERATE":

                from_asset = profile.moderate_asset

            else:

                from_asset = defensive.symbol

            #
            # Determine the asset we are entering
            #

            if strategy.new_state.name == "AGGRESSIVE":

                to_asset = profile.aggressive_asset

            elif strategy.new_state.name == "MODERATE":

                to_asset = profile.moderate_asset

            else:

                to_asset = defensive.symbol

            logger.info(
                "%-15s : SELL %s -> BUY %s",
                "Action",
                from_asset,
                to_asset,
            )

            logger.info(
                "%-15s : %s",
                "Reason",
                ", ".join(strategy.reasons),
            )

        logger.info("")

        logger.info(
            "%-15s : %s",
            "Aggressive",
            profile.aggressive_asset,
        )

        logger.info(
            "%-15s : %s",
            "Moderate",
            profile.moderate_asset,
        )

        logger.info(
            "%-15s : %s",
            "Defensive",
            defensive.symbol,
        )

        logger.info("")
        logger.info("Market Snapshot")
        logger.info("------------------------------")

        dashboard_assets = [

            asset

            for asset in MARKET_UNIVERSE

            if asset.dashboard

        ]

        groups = {}

        for asset in dashboard_assets:

            groups.setdefault(

                asset.dashboard_group,

                [],

            ).append(asset)


        for group_name, assets in groups.items():

            logger.info("")

            logger.info(
                "%s",
                group_name,
            )

            for asset in assets:

                dd = drawdown_from_2y_high(
                    market[asset.symbol],
                )

                history = market[asset.symbol]

                current_price = history.close.iloc[-1]

                logger.info(
                    "    %-7s %-38s %2dx   Peak $%8.2f   Now $%8.2f   %+.2f%%",
                    asset.symbol,
                    asset.description,
                    asset.leverage,
                    dd.peak_price,
                    current_price,
                    dd.drawdown * 100,
                )

        logger.info("")
        logger.info("QQQ")
        logger.info("------------------------------")

        logger.info(
            "Close          : %.2f",
            qqq.latest_close,
        )

        logger.info(
            "Date           : %s",
            qqq.last_date.date(),
        )

        logger.info("")
        logger.info("Indicators")
        logger.info("------------------------------")

        logger.info(
            "RVol           : %.2f%%",
            signals.rvol * 100,
        )

        logger.info(
            "VR             : %.2f",
            signals.vr,
        )

        logger.info(
            "SPY 200 SMA    : %+.2f%%",
            signals.spy_distance * 100,
        )

        logger.info(
            "Credit         : %+.2f%%",
            signals.credit * 100,
        )

        logger.info("")
        logger.info("Transition Status")
        logger.info("------------------------------")

        #
        # Current state
        #

        logger.info(
            "Current State  : %s",
            strategy.current_state.name,
        )

        logger.info(
            "Next State     : %s",
            strategy.new_state.name,
        )

        #
        # Moderate -> Defensive
        #

        if strategy.current_state.name == "MODERATE":

            logger.info("")
            logger.info("QLD -> Defensive")

            logger.info(
                "  RVol > %.2f%%       : %.2f%%   %s",
                self.profile.rvol_defensive * 100,
                signals.rvol * 100,
                "TRIGGERED"
                if signals.rvol_over_defensive
                else "clear",
            )

            logger.info(
                "  VR > %.2f           : %.2f     %s",
                self.profile.vr_defensive,
                signals.vr,
                "TRIGGERED"
                if signals.vr_over_defensive
                else "clear",
            )

            logger.info(
                "  SPY breakdown       : %+.2f%%   %s",
                signals.spy_distance * 100,
                "TRIGGERED"
                if signals.spy_breakdown
                else "clear",
            )

            logger.info(
                "  Credit crisis       : %+.2f%%   %s",
                signals.credit * 100,
                "TRIGGERED"
                if signals.credit_crisis
                else "clear",
            )

            logger.info(
                "  Donchian confirm    : %s",
                "TRIGGERED"
                if signals.donchian_confirmed
                else "clear",
            )

        #
        # Moderate -> Aggressive
        #

        if strategy.current_state.name == "MODERATE":

            logger.info("")
            logger.info(
                "%s -> %s",
                self.profile.moderate_asset,
                self.profile.aggressive_asset,
            )

            logger.info(
                "  RVol < %5.2f%%       : %6.2f%%   %s",
                self.profile.rvol_recovery * 100,
                signals.rvol * 100,
                "PASS"
                if signals.rvol_clear
                else "BLOCKED",
            )

            logger.info(
                "  VR < %7.2f          : %6.2f     %s",
                self.profile.vr_recovery,
                signals.vr,
                "PASS"
                if signals.vr_clear
                else "BLOCKED",
            )

            logger.info(
                "  SPY > %+6.2f%%       : %+6.2f%%   %s",
                self.profile.spy_clear * 100,
                signals.spy_distance * 100,
                "PASS"
                if signals.spy_clear
                else "BLOCKED",
            )

        #
        # Defensive -> Moderate
        #

        if strategy.current_state.name == "DEFENSIVE":

            logger.info("")
            logger.info("Defensive -> QLD")

            logger.info(
                "  RVol clear          : %.2f%%   %s",
                signals.rvol * 100,
                "PASS"
                if signals.rvol_defensive_clear
                else "BLOCKED",
            )

            logger.info(
                "  VR clear            : %.2f     %s",
                signals.vr,
                "PASS"
                if signals.vr_defensive_clear
                else "BLOCKED",
            )

            logger.info(
                "  SPY recovery        : %+.2f%%   %s",
                signals.spy_distance * 100,
                "PASS"
                if signals.spy_recovery
                else "BLOCKED",
            )

            logger.info(
                "  Donchian recovery   : %s",
                "PASS"
                if signals.donchian_recovered
                else "BLOCKED",
            )

        logger.info("")
        logger.info("Defensive Asset")
        logger.info("------------------------------")

        logger.info(
            "Current Choice : %s",
            defensive.symbol,
        )