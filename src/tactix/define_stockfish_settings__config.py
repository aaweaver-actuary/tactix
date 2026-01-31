from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import chess
import chess.engine


def _env_str(name: str, default: str) -> str:
    return os.getenv(name, default)


def _env_str_or_none(*names: str) -> str | None:
    for name in names:
        value = os.getenv(name)
        if value:
            return value
    return None


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_int_or_none(name: str) -> int | None:
    value = int(os.getenv(name, "0"))
    return value or None


def _env_bool(name: str, default: bool) -> bool:
    fallback = "1" if default else "0"
    return os.getenv(name, fallback) == "1"


@dataclass(slots=True)
class StockfishSettings:
    """Stockfish engine configuration."""

    path: Path = Path(_env_str("STOCKFISH_PATH", "stockfish"))
    checksum: str | None = _env_str_or_none("STOCKFISH_SHA256", "STOCKFISH_CHECKSUM")
    checksum_mode: str = _env_str("STOCKFISH_CHECKSUM_MODE", "warn")
    threads: int = _env_int("STOCKFISH_THREADS", 1)
    hash_mb: int = _env_int("STOCKFISH_HASH", 256)
    movetime_ms: int = _env_int("STOCKFISH_MOVETIME_MS", 150)
    depth: int | None = _env_int_or_none("STOCKFISH_DEPTH")
    multipv: int = _env_int("STOCKFISH_MULTIPV", 3)
    skill_level: int = _env_int("STOCKFISH_SKILL_LEVEL", 20)
    limit_strength: bool = _env_bool("STOCKFISH_LIMIT_STRENGTH", False)
    uci_elo: int | None = _env_int_or_none("STOCKFISH_UCI_ELO")
    uci_analyse_mode: bool = _env_bool("STOCKFISH_UCI_ANALYSE_MODE", True)
    use_nnue: bool = _env_bool("STOCKFISH_USE_NNUE", True)
    ponder: bool = _env_bool("STOCKFISH_PONDER", False)
    random_seed: int | None = _env_int_or_none("STOCKFISH_RANDOM_SEED")
    max_retries: int = _env_int("STOCKFISH_MAX_RETRIES", 2)
    retry_backoff_ms: int = _env_int("STOCKFISH_RETRY_BACKOFF_MS", 250)

    @property
    def limit(self) -> chess.engine.Limit:
        """Get the analysis limit based on depth or movetime.

        Returns:
            A `chess.engine.Limit` instance configured with depth or time.
        """

        return _build_stockfish_limit(self.depth, self.movetime_ms)


def _build_stockfish_limit(depth: int | None, movetime_ms: int) -> chess.engine.Limit:
    if depth:
        return chess.engine.Limit(depth=depth)
    return chess.engine.Limit(time=movetime_ms / 1000)
