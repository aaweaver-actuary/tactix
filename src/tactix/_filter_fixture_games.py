"""Filter fixture PGNs by timestamp window."""

from tactix._fixture_payload import _fixture_payload
from tactix._should_include_fixture import _should_include_fixture
from tactix.extract_last_timestamp_ms import extract_last_timestamp_ms


def _filter_fixture_games(
    chunks: list[str],
    user: str,
    source: str,
    since_ms: int,
    until_ms: int | None,
) -> list[dict[str, object]]:
    games: list[dict[str, object]] = []
    for raw in chunks:
        last_ts = extract_last_timestamp_ms(raw)
        if not _should_include_fixture(last_ts, since_ms, until_ms):
            continue
        games.append(_fixture_payload(raw, user, source, last_ts))
    return games
