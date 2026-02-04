"""Extract positions from PGN data using Python or Rust fallback."""

from __future__ import annotations

import importlib
import os

from tactix._extract_positions_fallback import _extract_positions_fallback
from tactix._extract_positions_python import _extract_positions_python
from tactix.build_extractor_request import build_extractor_request
from tactix.extract_positions_with_fallback__pgn import _extract_positions_with_fallback
from tactix.extractor_context import ExtractorDependencies, ExtractorRequest
from tactix.pgn_context_kwargs import PgnContextInputs
from tactix.utils import Logger, funclogger

logger = Logger(__name__)


@funclogger
def extract_positions(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> list[dict[str, object]]:
    """Extract positions from a PGN string."""
    request = build_extractor_request(
        PgnContextInputs(pgn, user, source, game_id, side_to_move_filter)
    )
    return _extract_positions_with_fallback(
        request,
        ExtractorDependencies(
            getenv=os.getenv,
            load_rust_extractor=_load_rust_extractor,
            call_rust_extractor=_call_rust_extractor,
            extract_positions_fallback=_extract_positions_fallback,
        ),
    )


@funclogger
def _load_rust_extractor():
    try:
        _core = importlib.import_module("tactix._core")
    except ImportError:  # pragma: no cover - optional Rust extension
        return None
    return getattr(_core, "extract_positions", None)


@funclogger
def _call_rust_extractor(
    rust_extractor,
    request: ExtractorRequest,
) -> list[dict[str, object]]:
    try:
        result = rust_extractor(
            request.pgn,
            request.user,
            request.source,
            request.game_id,
            request.side_to_move_filter,
        )
        return (
            _extract_positions_fallback(request)
            if not result and "[SetUp" in request.pgn
            else result
        )
    except (RuntimeError, TypeError, ValueError) as exc:  # pragma: no cover - rust fallback
        logger.warning("Rust extractor failed; falling back to Python: %s", exc)
        return _extract_positions_fallback(request)


__all__ = [
    "_call_rust_extractor",
    "_extract_positions_python",
    "_load_rust_extractor",
    "extract_positions",
]
