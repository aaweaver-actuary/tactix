"""Motif scope helpers for the current release."""

from __future__ import annotations

from tactix.analyze_tactics__positions import MATE_IN_ONE

ALLOWED_MOTIFS: tuple[str, ...] = (
    "hanging_piece",
    "mate",
)

ALL_MOTIFS: tuple[str, ...] = (
    "mate",
    "hanging_piece",
    "fork",
    "pin",
    "skewer",
    "discovered_attack",
    "discovered_check",
    "capture",
    "check",
    "escape",
)

FUTURE_MOTIFS: tuple[str, ...] = tuple(motif for motif in ALL_MOTIFS if motif not in ALLOWED_MOTIFS)


def is_supported_motif(motif: str | None, mate_in: int | None = None) -> bool:
    """Return True when a motif is within the current release scope."""
    if not motif:
        return False
    if motif == "hanging_piece":
        return True
    if motif == "mate":
        return mate_in == MATE_IN_ONE
    return False


def is_scoped_motif_row(motif: str | None, mate_type: str | None = None) -> bool:
    """Return True when a stored motif row is within the release scope."""
    if not motif:
        return False
    if motif == "hanging_piece":
        return True
    if motif == "mate":
        return mate_type is not None
    return False


def is_allowed_motif_filter(motif: str | None) -> bool:
    """Return True when a motif filter is within the allowed list."""
    if motif is None:
        return True
    return motif in ALLOWED_MOTIFS


def allowed_motif_list() -> tuple[str, ...]:
    """Return the motifs surfaced by the current release."""
    return ALLOWED_MOTIFS


__all__ = [
    "ALLOWED_MOTIFS",
    "ALL_MOTIFS",
    "FUTURE_MOTIFS",
    "allowed_motif_list",
    "is_allowed_motif_filter",
    "is_scoped_motif_row",
    "is_supported_motif",
]
