"""
Historical and synthetic leveraged ETF split schedules.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)


class LeveragedSplitManager:

    QLD_INCEPTION = pd.Timestamp("2006-06-21")

    @staticmethod
    def split_schedule_path() -> Path:
        return (
            Path(__file__).resolve().parents[2]
            / "cache"
            / "simulatedTQQQ.csv"
        )

    @classmethod
    def load_simulated_tqqq(cls) -> pd.DataFrame:
        path = cls.split_schedule_path()

        if not path.exists():
            raise FileNotFoundError(
                "Historical TQQQ simulation file was not found:\n"
                f"    {path}"
            )

        df = pd.read_csv(path)

        required = {
            "date",
            "close",
            "split",
        }

        missing = required.difference(df.columns)

        if missing:
            raise ValueError(
                "simulatedTQQQ.csv is missing required columns: "
                f"{sorted(missing)}"
            )

        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce",
        )

        df["close"] = pd.to_numeric(
            df["close"],
            errors="coerce",
        )

        df["split"] = pd.to_numeric(
            df["split"],
            errors="coerce",
        ).fillna(1.0)

        df = df.dropna(
            subset=[
                "date",
                "close",
            ]
        )

        df = df[df["close"] > 0]

        df["split"] = df["split"].where(
            df["split"] > 0,
            1.0,
        )

        df = (
            df.sort_values("date")
            .drop_duplicates(
                subset=["date"],
                keep="last",
            )
            .set_index("date")
        )

        logger.info(
            "Loaded simulated TQQQ reference: "
            f"{len(df)} rows, "
            f"{df.index.min().date()} -> "
            f"{df.index.max().date()}"
        )

        return df

    @classmethod
    def load_tqqq_schedule(
        cls,
    ) -> dict[pd.Timestamp, float]:

        df = cls.load_simulated_tqqq()

        schedule = {}

        for date, row in df.iterrows():

            factor = float(row["split"])

            if (
                not math.isfinite(factor)
                or factor <= 0
                or math.isclose(factor, 1.0)
            ):
                continue

            schedule[pd.Timestamp(date)] = factor

        logger.info(
            "TQQQ historical split schedule loaded: "
            f"{len(schedule)} events"
        )

        for date, factor in schedule.items():
            logger.info(
                f"    {date.date()} : split {factor:g}"
            )

        return schedule

    @classmethod
    def get_schedule(
        cls,
        symbol: str,
    ) -> dict[pd.Timestamp, float]:

        symbol = symbol.upper()

        if symbol == "TQQQ":
            return cls.load_tqqq_schedule()

        return {}

    @classmethod
    def build_series(
        cls,
        symbol: str,
        index: pd.DatetimeIndex,
    ) -> pd.Series:

        splits = pd.Series(
            1.0,
            index=index,
            dtype=float,
        )

        schedule = cls.get_schedule(symbol)

        for date, factor in schedule.items():

            if date in splits.index:
                splits.loc[date] = factor

        return splits