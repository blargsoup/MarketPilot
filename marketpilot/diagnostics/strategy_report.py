class StrategyReport:

    def display(
        self,
        logger,
        diagnostics,
    ):

        logger.info("")
        logger.info("=" * 70)
        logger.info("STRATEGY DIAGNOSTICS")
        logger.info("=" * 70)

        logger.info("")
        logger.info("Days")

        logger.info(
            "    Aggressive : %d",
            diagnostics.aggressive_days,
        )

        logger.info(
            "    Moderate   : %d",
            diagnostics.moderate_days,
        )

        logger.info(
            "    Defensive  : %d",
            diagnostics.defensive_days,
        )

        logger.info("")
        logger.info("Transitions")

        logger.info(
            "    Agg -> Mod : %d",
            diagnostics.aggressive_to_moderate,
        )

        logger.info(
            "    Mod -> Agg : %d",
            diagnostics.moderate_to_aggressive,
        )

        logger.info(
            "    Mod -> Def : %d",
            diagnostics.moderate_to_defensive,
        )

        logger.info(
            "    Def -> Mod : %d",
            diagnostics.defensive_to_moderate,
        )

        logger.info("")
        logger.info("Moderate Gate Diagnostics")

        logger.info(
            "    Days checked : %d",
            diagnostics.moderate_days_checked,
        )

        logger.info(
            "    Blocked RVol : %d",
            diagnostics.blocked_rvol,
        )

        logger.info(
            "    Blocked VR   : %d",
            diagnostics.blocked_vr,
        )

        logger.info(
            "    Blocked SPY  : %d",
            diagnostics.blocked_spy,
        )

        logger.info("")

        logger.info(
            "    Passed RVol  : %d",
            diagnostics.passed_rvol,
        )

        logger.info(
            "    Passed VR    : %d",
            diagnostics.passed_vr,
        )

        logger.info(
            "    Passed SPY   : %d",
            diagnostics.passed_spy,
        )

        logger.info("")

        logger.info(
            "    ALL CLEAR    : %d",
            diagnostics.all_clear,
        )

        logger.info("")