"""Build an empty conversion payload for pipelines."""

from __future__ import annotations

from tactix.config import Settings
from tactix.conversion_payload__pipeline import _build_conversion_payload


def _empty_conversion_payload(settings: Settings) -> dict[str, object]:
    """Return a zeroed conversion payload."""
    return _build_conversion_payload(
        settings,
        games=0,
        inserted_games=0,
        positions=0,
    )
