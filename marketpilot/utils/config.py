"""
Configuration loading utilities.
"""

import json
from pathlib import Path


class Config:

    def __init__(self):

        root = Path(__file__).resolve().parents[2]

        self.settings = self._load(
            root / "config" / "settings.json"
        )

        self.thresholds = self._load(
            root / "config" / "thresholds.json"
        )

    @staticmethod
    def _load(path):

        with open(path, "r", encoding="utf8") as file:

            return json.load(file)