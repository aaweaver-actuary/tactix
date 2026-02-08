"""Normalize side-to-move filters."""

from tactix.position_context_builder import logger


def _normalize_side_filter(side_to_move_filter: str | None) -> str | None:
    """Normalize a side filter value or return None."""
    if not side_to_move_filter:
        return None
    normalized = side_to_move_filter.strip().lower()
    if normalized in {"white", "black"}:
        return normalized
    logger.warning("Unknown side_to_move_filter: %s", side_to_move_filter)
    return None
