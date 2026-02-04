"""Public wrapper for extracting positions from PGNs."""

from tactix._fallback_kwargs import _fallback_kwargs
from tactix.extract_positions_with_fallback__pgn import _extract_positions_with_fallback
from tactix.extractor_context import ExtractorRequest


def extract_positions(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> list[dict[str, object]]:
    """Extract positions from PGN text with Rust/Python fallback."""
    request = ExtractorRequest(
        pgn=pgn,
        user=user,
        source=source,
        game_id=game_id,
        side_to_move_filter=side_to_move_filter,
    )
    return _extract_positions_with_fallback(request, _fallback_kwargs())
