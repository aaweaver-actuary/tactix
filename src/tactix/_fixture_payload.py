"""Build fixture payload rows for PGN inputs."""

from datetime import UTC, datetime

from tactix._ensure_chesscom_site_url import _ensure_chesscom_site_url
from tactix.extract_game_id import extract_game_id


def _fixture_payload(
    pgn: str,
    user: str,
    source: str,
    last_ts: int,
) -> dict[str, object]:
    if source == "chesscom":
        pgn = _ensure_chesscom_site_url(pgn)
    return {
        "game_id": extract_game_id(pgn),
        "user": user,
        "source": source,
        "fetched_at": datetime.now(UTC),
        "pgn": pgn,
        "last_timestamp_ms": last_ts,
    }
