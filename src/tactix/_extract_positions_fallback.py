"""Python fallback for position extraction."""

# pylint: disable=import-outside-toplevel,protected-access

from tactix._extract_positions_python import _extract_positions_python
from tactix.extractor_context import ExtractorRequest


def _extract_positions_fallback(
    request: ExtractorRequest,
) -> list[dict[str, object]]:
    """Extract positions using the pure-Python implementation."""
    return _extract_positions_python(
        request.pgn,
        request.user,
        request.source,
        request.game_id,
        side_to_move_filter=request.side_to_move_filter,
    )
