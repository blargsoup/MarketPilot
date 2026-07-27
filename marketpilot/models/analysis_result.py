from __future__ import annotations

from dataclasses import dataclass


@dataclass
class AnalysisResult:

    market: dict
    signals: "SignalEngine"
    strategy: "StrategyResult"
    defensive: "DefensiveSelection"

    backtest: object | None = None
    statistics: object | None = None