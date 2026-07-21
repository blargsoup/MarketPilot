from marketpilot import __version__

from marketpilot.utils.logger import setup_logger
from marketpilot.utils.config import Config
from marketpilot.data import MarketDataService


def main():

    logger = setup_logger()

    logger.info("=========================================")
    logger.info("MarketPilot %s", __version__)
    logger.info("=========================================")

    Config()

    data = MarketDataService()

    history = data.get_history("QQQ")

    logger.info("")

    logger.info("First Date : %s", history.index[0].date())
    logger.info("Last Date  : %s", history.index[-1].date())

    logger.info("Rows       : %d", len(history))

    logger.info("")

    logger.info("Latest Close : %.2f", history["Close"].iloc[-1])

    logger.info("")

    logger.info("Done.")


if __name__ == "__main__":

    main()