from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from marketpilot.signals import SignalEngine
    from marketpilot.strategies import StrategyResult
    from marketpilot.defensive import DefensiveSelection


@dataclass
class AnalysisResult:

    market: dict
    signals: SignalEngine
    strategy: StrategyResult
    defensive: DefensiveSelection

    backtest: object | None = None
    statistics: object | None = None