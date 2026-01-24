from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


DEFAULT_DATA_DIR = Path(os.getenv("TACTIX_DATA_DIR", "data"))


@dataclass(slots=True)
class Settings:
    """Central configuration for ingestion, analysis, and UI refresh."""

    user: str = os.getenv("LICHESS_USER", "lichess")
    source: str = os.getenv("TACTIX_SOURCE", "lichess")
    lichess_token: Optional[str] = os.getenv("LICHESS_TOKEN")
    duckdb_path: Path = Path(
        os.getenv("TACTIX_DUCKDB_PATH", DEFAULT_DATA_DIR / "tactix.duckdb")
    )
    checkpoint_path: Path = Path(
        os.getenv("TACTIX_CHECKPOINT_PATH", DEFAULT_DATA_DIR / "lichess_since.txt")
    )
    stockfish_path: Path = Path(os.getenv("STOCKFISH_PATH", "stockfish"))
    stockfish_threads: int = int(os.getenv("STOCKFISH_THREADS", "1"))
    stockfish_hash_mb: int = int(os.getenv("STOCKFISH_HASH", "256"))
    stockfish_movetime_ms: int = int(os.getenv("STOCKFISH_MOVETIME_MS", "150"))
    stockfish_depth: Optional[int] = int(os.getenv("STOCKFISH_DEPTH", "0")) or None
    stockfish_multipv: int = int(os.getenv("STOCKFISH_MULTIPV", "3"))
    metrics_version_file: Path = Path(
        os.getenv(
            "TACTIX_METRICS_VERSION_PATH", DEFAULT_DATA_DIR / "metrics_version.txt"
        )
    )
    rapid_perf: str = os.getenv("TACTIX_PERF", "rapid")
    fixture_pgn_path: Path = Path(
        os.getenv("TACTIX_FIXTURE_PGN_PATH", "tests/fixtures/lichess_rapid_sample.pgn")
    )
    use_fixture_when_no_token: bool = os.getenv("TACTIX_USE_FIXTURE", "1") == "1"

    @property
    def data_dir(self) -> Path:
        return self.duckdb_path.parent

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_version_file.parent.mkdir(parents=True, exist_ok=True)


def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_dirs()
    return settings
