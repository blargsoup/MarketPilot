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

    logger.info("First Date : %s", history.first_date.date())
    logger.info("Last Date  : %s", history.last_date.date())

    logger.info("Rows       : %d", history.rows)

    logger.info("")

    logger.info(
        "Latest Close : %.2f",
        history.latest_close,
    )

    logger.info(
        "Latest Volume : %.0f",
        history.latest_volume,
    )

    logger.info("Done.")


if __name__ == "__main__":

    main()