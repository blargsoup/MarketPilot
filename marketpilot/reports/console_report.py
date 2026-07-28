"""
Console reporting.
"""

from marketpilot import __version__
from marketpilot.data import MARKET_UNIVERSE
class ConsoleReport:

    def __init__(self, logger):

        self.logger = logger
    
    def display(
        self,
        analysis,
    ):

        stats = analysis.statistics

        market = analysis.market

        signals = analysis.signals

        result = analysis.strategy

        defensive = analysis.defensive

        logger = self.logger

        qqq = market["QQQ"]

        logger.info("=========================================")
        logger.info(
            "MarketPilot %s",
            __version__,
        )
        logger.info("=========================================")

        logger.info("")
        logger.info("Market Universe")
        logger.info("------------------------------")

        for asset in MARKET_UNIVERSE:

            logger.info(
                "%-7s %-30s %s",
                asset.symbol,
                asset.description,
                f"({asset.category})",
            )

        logger.info("")


        #
        # QQQ Summary
        #

        logger.info("")
        logger.info("QQQ Summary")
        logger.info("------------------------------")

        logger.info(
            "First Date : %s",
            qqq.first_date.date(),
        )

        logger.info(
            "Last Date  : %s",
            qqq.last_date.date(),
        )

        logger.info(
            "Rows       : %d",
            qqq.rows,
        )

        logger.info("")

        logger.info(
            "Latest Close : %.2f",
            qqq.latest_close,
        )

        logger.info(
            "Latest Volume : %.0f",
            qqq.latest_volume,
        )

        #
        # Indicators
        #

        logger.info("")
        logger.info("Indicators")
        logger.info("------------------------------")

        logger.info(
            "RVol (21d) : %.2f%%",
            signals.rvol * 100,
        )

        logger.info(
            "VR         : %.2f",
            signals.vr,
        )

        logger.info(
            "SPY vs 200 SMA : %.2f%%",
            signals.spy_distance,
        )

        logger.info(
            "Credit (20d): %.2f%%",
            signals.credit,
        )

        #
        # Boolean Signals
        #

        logger.info("")
        logger.info("Boolean Signals")
        logger.info("------------------------------")

        logger.info(
            "RVol >18%%      : %s",
            signals.rvol_over_qld,
        )

        logger.info(
            "VR >1.25       : %s",
            signals.vr_over_qld,
        )

        logger.info(
            "SPY Breakdown  : %s",
            signals.spy_breakdown,
        )

        logger.info(
            "Credit Crisis  : %s",
            signals.credit_crisis,
        )

        logger.info(
            "Donchian Break : %s",
            signals.donchian_break,
        )

        logger.info(
            "Donchian+RVol  : %s",
            signals.donchian_confirmed,
        )

        #
        # Strategy
        #

        logger.info("")
        logger.info("Strategy")
        logger.info("------------------------------")

        logger.info(
            "Current State : %s",
            result.current_state.name,
        )

        logger.info(
            "New State     : %s",
            result.new_state.name,
        )

        logger.info(
            "Changed       : %s",
            "YES" if result.changed else "NO",
        )

        logger.info("")

        if result.reasons:

            for reason in result.reasons:

                logger.info(
                    "✓ %s",
                    reason,
                )

        else:

            logger.info(
                "No transition conditions met."
            )

        #
        # Defensive
        #

        logger.info("")
        logger.info("Defensive Asset")
        logger.info("------------------------------")

        logger.info(
            "Selected : %s",
            defensive.symbol,
        )

        logger.info(
            "30 Day Momentum : %.2f%%",
            defensive.momentum30,
        )

        logger.info(
            "90 Day Momentum : %.2f%%",
            defensive.momentum90,
        )

        logger.info("")
        logger.info("Performance")
        logger.info("------------------------------")

        logger.info(
            "Starting Value : $%s",
            format(stats.starting_value, ",.2f"),
        )

        logger.info(
            "Ending Value   : $%s",
            format(stats.ending_value, ",.2f"),
        )

        logger.info("")

        logger.info(
            "Total Return : %.2f%%",
            stats.total_return * 100,
        )

        logger.info(
            "Annual CAGR : %.2f%%",
            stats.annual_return * 100,
        )

        logger.info(
            "Max Drawdown : %.2f%%",
            stats.max_drawdown * 100,
        )

        logger.info("")

        logger.info(
            "Trades         : %d",
            stats.trades,
        )

        if analysis.backtest.benchmarks:
            logger.info("")
            logger.info("Buy & Hold Benchmarks")
            logger.info("%-8s %12s %10s %10s", "Symbol", "End Value", "CAGR", "Max DD")

            for benchmark in analysis.backtest.benchmarks:
                logger.info(
                    "%-8s $%10s %9.2f%% %9.2f%%",
                    benchmark.symbol,
                    format(benchmark.ending_value, ",.0f"),
                    benchmark.annual_return * 100,
                    benchmark.max_drawdown * 100,
                )

        if hasattr(analysis, "strategy_comparisons"):
            logger.info("")
            logger.info("Strategy Comparison")
            logger.info(
                "%-20s %10s %10s %10s",
                "Strategy",
                "End Value",
                "CAGR",
                "Max DD",
            )

            for comparison in analysis.strategy_comparisons:
                comparison_stats = comparison.statistics
                logger.info(
                    "%-20s $%8s %9.2f%% %9.2f%%",
                    comparison.name,
                    format(comparison_stats.ending_value, ",.0f"),
                    comparison_stats.annual_return * 100,
                    comparison_stats.max_drawdown * 100,
                )

        logger.info("")

        logger.info("Done.")
