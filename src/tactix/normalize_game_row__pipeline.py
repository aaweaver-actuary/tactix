from __future__ import annotations

from collections.abc import Mapping
from datetime import UTC, datetime

from tactix.coerce_int__pipeline import _coerce_int
from tactix.coerce_pgn__pipeline import _coerce_pgn
from tactix.coerce_str__pipeline import _coerce_str
from tactix.config import Settings
from tactix.pipeline_state__pipeline import GameRow


def _normalize_game_row(row: Mapping[str, object], settings: Settings) -> GameRow:
    fetched_at = row.get("fetched_at")
    if not isinstance(fetched_at, datetime):
        fetched_at = datetime.now(UTC)
    return {
        "game_id": _coerce_str(row.get("game_id")),
        "user": _coerce_str(row.get("user")) or settings.user,
        "source": _coerce_str(row.get("source")) or settings.source,
        "fetched_at": fetched_at,
        "pgn": _coerce_pgn(row.get("pgn")),
        "last_timestamp_ms": _coerce_int(row.get("last_timestamp_ms")),
    }
