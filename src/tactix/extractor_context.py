"""Context objects for position extraction dependencies."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class ExtractorRequest:
    """Input parameters for position extraction."""

    pgn: str
    user: str
    source: str
    game_id: str | None
    side_to_move_filter: str | None


@dataclass(frozen=True)
class ExtractorDependencies:
    """Dependency callbacks for position extraction."""

    getenv: Callable[[str], str | None]
    load_rust_extractor: Callable[[], object | None]
    call_rust_extractor: Callable[[object, ExtractorRequest], list[dict[str, object]]]
    extract_positions_fallback: Callable[[ExtractorRequest], list[dict[str, object]]]
