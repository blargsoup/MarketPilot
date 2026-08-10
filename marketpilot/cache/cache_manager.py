"""
Handles loading and saving cached market data.
"""

from pathlib import Path
from datetime import datetime

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

    def modified_time(
        self,
        symbol: str,
    ) -> datetime:

        return datetime.fromtimestamp(
            self.cache_file(symbol).stat().st_mtime
        )

    def is_fresh(
        self,
        symbol: str,
    ) -> bool:

        if not self.exists(symbol):
            return False

        modified = self.modified_time(symbol).date()
        today = datetime.now().date()

        return modified == today