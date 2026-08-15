"""
Static historical market-data provider.

Loads repository-provided synthetic historical datasets from TSV files.

These files are treated as authoritative historical research data. The
provider does not attempt to reconstruct leveraged ETF returns, financing
costs, splits, or ETF inception handoffs.
"""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

from .provider import MarketDataProvider


class SyntheticDataProvider(MarketDataProvider):
    """
    Loads static synthetic historical price data from repository TSV files.
    """

    SYMBOL_FILES = {
        "QQQ": "synthetic-qqq.tsv",
        "QLD": "synthetic-qld.tsv",
        "TQQQ": "synthetic-tqqq.tsv",
        "SSO": "synthetic-sso.tsv",
        "SPXL": "synthetic-spxl.tsv",
        "SQQQ": "synthetic-sqqq.tsv",
    }

    def __init__(self):
        self.logger = logging.getLogger("MarketPilot")

        self.cache_directory = (
            Path(__file__).resolve().parents[2]
            / "cache"
        )

    def get_history(
        self,
        symbol: str,
        period: str = "max",
        interval: str = "1d",
    ) -> pd.DataFrame:

        symbol = symbol.upper()

        if symbol not in self.SYMBOL_FILES:
            raise ValueError(
                f"SyntheticDataProvider does not support "
                f"symbol '{symbol}'. "
                f"Supported symbols: "
                f"{sorted(self.SYMBOL_FILES)}"
            )

        if interval != "1d":
            raise ValueError(
                "Synthetic historical data currently supports "
                "daily interval only."
            )

        filename = self.SYMBOL_FILES[symbol]
        path = self.cache_directory / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Synthetic historical data was not found:\n"
                f"    {path}"
            )

        self.logger.info(
            "Loading synthetic historical data for %s...",
            symbol,
        )

        df = pd.read_csv(
            path,
            sep="\t",
        )

        if df.empty:
            raise RuntimeError(
                f"Synthetic dataset for {symbol} is empty: "
                f"{path}"
            )

        # --------------------------------------------------------------
        # Normalize columns.
        # --------------------------------------------------------------

        df.columns = [
            str(column).strip()
            for column in df.columns
        ]

        if "Date" not in df.columns:
            raise ValueError(
                f"Synthetic dataset for {symbol} is missing "
                f"'Date' column. Columns: {list(df.columns)}"
            )

        if "Close" not in df.columns:
            raise ValueError(
                f"Synthetic dataset for {symbol} is missing "
                f"'Close' column. Columns: {list(df.columns)}"
            )

        # --------------------------------------------------------------
        # Parse dates.
        # --------------------------------------------------------------

        df["Date"] = pd.to_datetime(
            df["Date"],
            errors="coerce",
        )

        if df["Date"].isna().any():
            bad_rows = int(
                df["Date"].isna().sum()
            )

            raise ValueError(
                f"Synthetic dataset for {symbol} contains "
                f"{bad_rows} invalid dates."
            )

        df = df.set_index("Date")
        df.index.name = None

        df = df.sort_index()

        # --------------------------------------------------------------
        # Validate duplicate dates.
        # --------------------------------------------------------------

        if df.index.has_duplicates:
            duplicate_count = int(
                df.index.duplicated().sum()
            )

            raise ValueError(
                f"Synthetic dataset for {symbol} contains "
                f"{duplicate_count} duplicate dates."
            )

        # --------------------------------------------------------------
        # Validate Close.
        # --------------------------------------------------------------

        df["Close"] = pd.to_numeric(
            df["Close"],
            errors="coerce",
        )

        if df["Close"].isna().any():
            bad_rows = int(
                df["Close"].isna().sum()
            )

            raise ValueError(
                f"Synthetic dataset for {symbol} contains "
                f"{bad_rows} invalid Close values."
            )

        if (df["Close"] <= 0).any():
            bad_date = df.index[
                df["Close"] <= 0
            ][0]

            bad_value = df.loc[
                bad_date,
                "Close",
            ]

            raise ValueError(
                f"Synthetic dataset for {symbol} contains "
                f"non-positive Close value {bad_value} "
                f"on {bad_date}."
            )

        # --------------------------------------------------------------
        # Build the same basic OHLC structure expected by MarketPilot.
        #
        # The source TSV contains only Date + Close.
        #
        # We intentionally do NOT invent intraday prices.
        # --------------------------------------------------------------

        close = df["Close"].astype(float)

        result = pd.DataFrame(
            {
                "Open": close,
                "High": close,
                "Low": close,
                "Close": close,
                "Volume": 0,
            },
            index=df.index,
        )

        self.logger.info(
            "%s synthetic history loaded successfully "
            "(%d rows, %s -> %s)",
            symbol,
            len(result),
            result.index.min().date(),
            result.index.max().date(),
        )

        self.logger.info(
            "%s synthetic latest close: %.6f",
            symbol,
            float(result["Close"].iloc[-1]),
        )

        return result