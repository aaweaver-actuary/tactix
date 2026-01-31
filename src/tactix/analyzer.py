from __future__ import annotations

from dataclasses import dataclass

from tactix.stockfish_engine import StockfishEngine


@dataclass
class TacticsAnalyzer:
    """Analyzer for Tactics data."""

    engine: StockfishEngine

    def analyze(self, data):
        """Analyze the given data."""
