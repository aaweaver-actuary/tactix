"""Python fallback for position extraction."""

import importlib

from tactix._extract_positions_python import _extract_positions_python
from tactix.extractor_context import ExtractorRequest


def _resolve_position_extractor() -> object | None:
    try:
        return importlib.import_module("tactix.extract_positions__pgn")
    except ImportError:  # pragma: no cover - optional dependency in some environments
        return None


def _extract_positions_fallback(
    request: ExtractorRequest,
) -> list[dict[str, object]]:
    """Extract positions using the pure-Python implementation."""
    extractor = _resolve_position_extractor()
    if extractor is None:
        extractor_fn = _extract_positions_python
    else:
        extractor_fn = getattr(extractor, "_extract_positions_python", _extract_positions_python)
    return extractor_fn(
        request.pgn,
        request.user,
        request.source,
        request.game_id,
        side_to_move_filter=request.side_to_move_filter,
    )
