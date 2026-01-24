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

    user: str = os.getenv("TACTIX_USER", os.getenv("LICHESS_USER", "lichess"))
    lichess_user: str = os.getenv("LICHESS_USER", "lichess")
    source: str = os.getenv("TACTIX_SOURCE", "lichess")
    lichess_token: Optional[str] = os.getenv("LICHESS_TOKEN")
    chesscom_user: str = os.getenv("CHESSCOM_USER", "chesscom")
    chesscom_token: Optional[str] = os.getenv("CHESSCOM_TOKEN")
    chesscom_time_class: str = os.getenv("CHESSCOM_TIME_CLASS", "blitz")
    duckdb_path: Path = Path(
        os.getenv("TACTIX_DUCKDB_PATH", DEFAULT_DATA_DIR / "tactix.duckdb")
    )
    checkpoint_path: Path = Path(
        os.getenv("TACTIX_CHECKPOINT_PATH", DEFAULT_DATA_DIR / "lichess_since.txt")
    )
    chesscom_checkpoint_path: Path = Path(
        os.getenv(
            "TACTIX_CHESSCOM_CHECKPOINT_PATH", DEFAULT_DATA_DIR / "chesscom_since.txt"
        )
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
    chesscom_fixture_pgn_path: Path = Path(
        os.getenv(
            "TACTIX_CHESSCOM_FIXTURE_PGN_PATH",
            "tests/fixtures/chesscom_blitz_sample.pgn",
        )
    )
    use_fixture_when_no_token: bool = os.getenv("TACTIX_USE_FIXTURE", "1") == "1"
    chesscom_use_fixture_when_no_token: bool = (
        os.getenv("TACTIX_CHESSCOM_USE_FIXTURE", "1") == "1"
    )

    @property
    def data_dir(self) -> Path:
        return self.duckdb_path.parent

    def apply_source_defaults(self) -> None:
        self.source = (self.source or "lichess").lower()
        if self.source == "chesscom":
            self.user = self.chesscom_user
            self.checkpoint_path = self.chesscom_checkpoint_path
            self.fixture_pgn_path = self.chesscom_fixture_pgn_path
            self.use_fixture_when_no_token = self.chesscom_use_fixture_when_no_token
        elif not self.user:
            self.user = self.lichess_user

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.chesscom_checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        self.metrics_version_file.parent.mkdir(parents=True, exist_ok=True)


def get_settings(source: str | None = None) -> Settings:
    settings = Settings()
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.ensure_dirs()
    return settings
