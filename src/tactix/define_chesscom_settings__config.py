from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from tactix.define_config_defaults__config import DEFAULT_CHESSCOM_CHECKPOINT


@dataclass(slots=True)
class ChesscomSettings:
    """Chess.com-specific configuration."""

    user: str = os.getenv("CHESSCOM_USERNAME", os.getenv("CHESSCOM_USER", "chesscom"))
    token: str | None = os.getenv("CHESSCOM_TOKEN")
    time_class: str = os.getenv("CHESSCOM_TIME_CLASS", "blitz")
    profile: str = os.getenv("TACTIX_CHESSCOM_PROFILE", "")
    max_retries: int = int(os.getenv("CHESSCOM_MAX_RETRIES", "3"))
    retry_backoff_ms: int = int(os.getenv("CHESSCOM_RETRY_BACKOFF_MS", "500"))
    checkpoint_path: Path = Path(
        os.getenv("TACTIX_CHESSCOM_CHECKPOINT_PATH", DEFAULT_CHESSCOM_CHECKPOINT)
    )
