from marketpilot import __version__

from marketpilot.utils.logger import setup_logger
from marketpilot.utils.config import Config


def main():

    logger = setup_logger()

    logger.info("====================================")
    logger.info("MarketPilot %s", __version__)
    logger.info("====================================")

    config = Config()

    logger.info("Configuration loaded.")

    logger.info("Data Provider : %s",
                config.settings["data_provider"])

    logger.info("Ready.")


if __name__ == "__main__":

    main()