"""
Handles loading and saving cached market data.
"""

from pathlib import Path

import pandas as pd


class CacheManager:

    def __init__(self):

        self.cache_dir = Path("cache")

        self.cache_dir.mkdir(exist_ok=True)

    def cache_file(
        self,
        symbol: str,
    ) -> Path:

        return self.cache_dir / f"{symbol}.parquet"

    def exists(
        self,
        symbol: str,
    ) -> bool:

        return self.cache_file(symbol).exists()

    def load(
        self,
        symbol: str,
    ) -> pd.DataFrame:

        return pd.read_parquet(
            self.cache_file(symbol)
        )

    def save(
        self,
        symbol: str,
        df: pd.DataFrame,
    ):

        df.to_parquet(
            self.cache_file(symbol)
        )