"""Persist Lichess checkpoint timestamps to disk."""

from __future__ import annotations

from pathlib import Path


def write_checkpoint(path: Path, since_ms: int) -> None:
    """Write a Lichess checkpoint value to disk.

    Args:
        path: Checkpoint path.
        since_ms: Timestamp value to persist.
    """

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(str(since_ms))
