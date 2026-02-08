"""Extract metadata fields from PGN headers."""

from collections.abc import Mapping

from tactix._normalize_header_value import _normalize_header_value
from tactix._parse_elo import _parse_elo
from tactix._parse_utc_start_ms import _parse_utc_start_ms
from tactix._resolve_user_rating import _resolve_user_rating


def _extract_metadata_from_headers(
    headers: Mapping[str, str],
    user: str,
) -> dict[str, object]:
    time_control = _normalize_header_value(headers.get("TimeControl"))
    white = _normalize_header_value(headers.get("White", ""))
    black = _normalize_header_value(headers.get("Black", ""))
    white_elo = _parse_elo(headers.get("WhiteElo"))
    black_elo = _parse_elo(headers.get("BlackElo"))
    rating = _resolve_user_rating(user, white, black, white_elo, black_elo)
    utc_date = _normalize_header_value(headers.get("UTCDate"))
    utc_time = _normalize_header_value(headers.get("UTCTime"))
    return {
        "user_rating": rating,
        "time_control": time_control,
        "white_player": white,
        "black_player": black,
        "white_elo": white_elo,
        "black_elo": black_elo,
        "result": _normalize_header_value(headers.get("Result")),
        "event": _normalize_header_value(headers.get("Event")),
        "site": _normalize_header_value(headers.get("Site")),
        "utc_date": utc_date,
        "utc_time": utc_time,
        "termination": _normalize_header_value(headers.get("Termination")),
        "start_timestamp_ms": _parse_utc_start_ms(utc_date, utc_time),
    }
