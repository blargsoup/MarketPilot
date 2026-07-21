"""
Logging utilities for MarketPilot.
"""

import logging


def setup_logger() -> logging.Logger:
    """
    Configure and return the application logger.
    """

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )

    logger = logging.getLogger("MarketPilot")

    return logger