"""Helpers for resolving unclear outcome inputs."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UnclearOutcomeParams:
    motif: str | None = None
    best_move: str | None = None
    user_move_uci: str | None = None
    swing: int | None = None
    threshold: int | None = None
