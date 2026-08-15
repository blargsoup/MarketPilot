"""
Historical and synthetic leveraged ETF split schedules.

This module owns split metadata only.

Important:
    Splits affect quoted share price and share count.

    Splits do NOT affect economic NAV.

TQQQ:
    Uses the repository's authoritative simulatedTQQQ.csv split schedule.

QLD:
    No synthetic historical splits are currently applied.

Other leveraged ETFs:
    No historical synthetic splits are currently applied.
"""

from __future__ import annotations

import logging
import math
from pathlib import Path

import pandas as pd


logger = logging.getLogger(__name__)


class LeveragedSplitManager:

    # ------------------------------------------------------------------
    # Repository reference
    # ------------------------------------------------------------------

    @staticmethod
    def split_schedule_path() -> Path:
        """
        Return the path to the repository's simulated TQQQ reference.
        """

        return (
            Path(__file__).resolve().parents[2]
            / "cache"
            / "simulatedTQQQ.csv"
        )

    # ------------------------------------------------------------------
    # Load simulated TQQQ reference
    # ------------------------------------------------------------------

    @classmethod
    def load_simulated_tqqq(
        cls,
    ) -> pd.DataFrame:
        """
        Load the repository's simulated TQQQ CSV.

        Required columns:

            date
            close
            split

        The split column is metadata only.
        """

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

        missing = required.difference(
            df.columns
        )

        if missing:
            raise ValueError(
                "simulatedTQQQ.csv is missing required columns: "
                f"{sorted(missing)}"
            )

        # --------------------------------------------------------------
        # Normalize columns.
        # --------------------------------------------------------------

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

        # --------------------------------------------------------------
        # Remove invalid rows.
        # --------------------------------------------------------------

        df = df.dropna(
            subset=[
                "date",
                "close",
            ]
        )

        df = df[
            df["close"] > 0
        ]

        df["split"] = df["split"].where(
            df["split"] > 0,
            1.0,
        )

        # --------------------------------------------------------------
        # Sort and deduplicate.
        # --------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # TQQQ split schedule
    # ------------------------------------------------------------------

    @classmethod
    def load_tqqq_schedule(
        cls,
    ) -> dict[pd.Timestamp, float]:
        """
        Load the authoritative TQQQ split schedule.

        CSV semantics:

            2.0  = 2-for-1 forward split
            3.0  = 3-for-1 forward split
            0.25 = 1-for-4 reverse split

        These events affect quoted share price only.
        """

        df = cls.load_simulated_tqqq()

        schedule: dict[
            pd.Timestamp,
            float,
        ] = {}

        for date, row in df.iterrows():

            factor = float(
                row["split"]
            )

            if (
                not math.isfinite(factor)
                or factor <= 0
                or math.isclose(
                    factor,
                    1.0,
                )
            ):
                continue

            schedule[
                pd.Timestamp(date)
            ] = factor

        logger.info(
            "TQQQ historical split schedule loaded: "
            f"{len(schedule)} events"
        )

        for date, factor in schedule.items():

            logger.info(
                f"    {date.date()} : "
                f"split {factor:g}"
            )

        return schedule

    # ------------------------------------------------------------------
    # Public schedule interface
    # ------------------------------------------------------------------

    @classmethod
    def get_schedule(
        cls,
        symbol: str,
    ) -> dict[pd.Timestamp, float]:
        """
        Return the historical split schedule for a symbol.

        Currently only TQQQ has an authoritative synthetic schedule.

        IMPORTANT:

            QLD deliberately returns no synthetic splits.

            We previously tested borrowing TQQQ's pre-inception split
            schedule for QLD. That experiment is now removed.
        """

        symbol = symbol.upper()

        if symbol == "TQQQ":

            return cls.load_tqqq_schedule()

        return {}

    # ------------------------------------------------------------------
    # Build aligned split series
    # ------------------------------------------------------------------

    @classmethod
    def build_series(
        cls,
        symbol: str,
        index: pd.DatetimeIndex,
    ) -> pd.Series:
        """
        Build a split series aligned to the supplied dates.

        Dates without a split event receive 1.0.
        """

        splits = pd.Series(
            1.0,
            index=index,
            dtype=float,
        )

        schedule = cls.get_schedule(
            symbol
        )

        for date, factor in schedule.items():

            if date in splits.index:

                splits.loc[date] = factor

        return splits