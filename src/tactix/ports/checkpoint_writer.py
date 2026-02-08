"""Port interface for pipeline checkpoint persistence."""

from __future__ import annotations

from pathlib import Path
from typing import Protocol


class CheckpointWriter(Protocol):
    """Persist pipeline checkpoints for external sources."""

    def write_chesscom_cursor(self, path: Path, cursor: str | None) -> None:
        """Write a chess.com cursor token to disk."""

    def write_lichess_checkpoint(self, path: Path, since_ms: int) -> None:
        """Write a Lichess checkpoint value to disk."""
