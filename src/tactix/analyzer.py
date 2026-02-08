"""Simple tactics analyzer wrapper."""

from __future__ import annotations

from dataclasses import dataclass

from tactix.StockfishEngine import StockfishEngine


@dataclass
class TacticsAnalyzer:
    """Analyzer for Tactics data."""

    engine: StockfishEngine

    def analyze(self, data):
        """Analyze the given data."""
