"""Default checkpoint writer implementation."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from tactix.infra.clients.chesscom_client import write_cursor
from tactix.infra.clients.lichess_client import write_checkpoint
from tactix.ports.checkpoint_writer import CheckpointWriter


@dataclass(frozen=True)
class DefaultCheckpointWriter(CheckpointWriter):
    """Default checkpoint writer using infra client helpers."""

    def write_chesscom_cursor(self, path: Path, cursor: str | None) -> None:
        write_cursor(path, cursor)

    def write_lichess_checkpoint(self, path: Path, since_ms: int) -> None:
        write_checkpoint(path, since_ms)
