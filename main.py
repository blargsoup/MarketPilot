from marketpilot import __version__

from marketpilot.utils.logger import setup_logger
from marketpilot.utils.config import Config
from marketpilot.data import MarketDataService
from marketpilot.signals import SignalEngine
from marketpilot.strategies import ARVolStrategy

def main():

    logger = setup_logger()

    logger.info("=========================================")
    logger.info("MarketPilot %s", __version__)
    logger.info("=========================================")

    Config()

    data = MarketDataService()

    symbols = [
        "QQQ",
        "SPY",
        "HYG",
        "LQD",
        "TLT",
        "GLD",
        "XLU",
        "XLE",
    ]

    market = data.get_histories(symbols)

    qqq = market["QQQ"]
    spy = market["SPY"]

    signals = SignalEngine(market)

    strategy = ARVolStrategy()

    result = strategy.evaluate(signals)

    logger.info("")
    logger.info("QQQ Summary")
    logger.info("------------------------------")

    logger.info("First Date : %s", qqq.first_date.date())
    logger.info("Last Date  : %s", qqq.last_date.date())
    logger.info("Rows       : %d", qqq.rows)

    logger.info("")
    logger.info("Latest Close : %.2f", qqq.latest_close)
    logger.info("Latest Volume : %.0f", qqq.latest_volume)

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

    logger.info("")
    logger.info("Strategy")
    logger.info("------------------------------")

    logger.info(
        "Recommended State : %s",
        result.state.value,
    )

    logger.info("")

    for reason in result.reasons:
        logger.info(reason)

    logger.info("Done.")


if __name__ == "__main__":

    main()