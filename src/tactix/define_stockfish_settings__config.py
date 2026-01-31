from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.engine


@dataclass(slots=True)
class StockfishSettings:
    """Stockfish engine configuration."""

    path: Path = Path(os.getenv("STOCKFISH_PATH", "stockfish"))
    checksum: str | None = os.getenv("STOCKFISH_SHA256") or os.getenv("STOCKFISH_CHECKSUM")
    checksum_mode: str = os.getenv("STOCKFISH_CHECKSUM_MODE", "warn")
    threads: int = int(os.getenv("STOCKFISH_THREADS", "1"))
    hash_mb: int = int(os.getenv("STOCKFISH_HASH", "256"))
    movetime_ms: int = int(os.getenv("STOCKFISH_MOVETIME_MS", "150"))
    depth: int | None = int(os.getenv("STOCKFISH_DEPTH", "0")) or None
    multipv: int = int(os.getenv("STOCKFISH_MULTIPV", "3"))
    skill_level: int = int(os.getenv("STOCKFISH_SKILL_LEVEL", "20"))
    limit_strength: bool = os.getenv("STOCKFISH_LIMIT_STRENGTH", "0") == "1"
    uci_elo: int | None = int(os.getenv("STOCKFISH_UCI_ELO", "0")) or None
    uci_analyse_mode: bool = os.getenv("STOCKFISH_UCI_ANALYSE_MODE", "1") == "1"
    use_nnue: bool = os.getenv("STOCKFISH_USE_NNUE", "1") == "1"
    ponder: bool = os.getenv("STOCKFISH_PONDER", "0") == "1"
    random_seed: int | None = int(os.getenv("STOCKFISH_RANDOM_SEED", "0")) or None
    max_retries: int = int(os.getenv("STOCKFISH_MAX_RETRIES", "2"))
    retry_backoff_ms: int = int(os.getenv("STOCKFISH_RETRY_BACKOFF_MS", "250"))

    @property
    def limit(self) -> chess.engine.Limit:
        """Get the analysis limit based on depth or movetime.

        Returns:
            A `chess.engine.Limit` instance configured with depth or time.
        """

        if self.depth:
            return chess.engine.Limit(depth=self.depth)
        return chess.engine.Limit(time=self.movetime_ms / 1000)
