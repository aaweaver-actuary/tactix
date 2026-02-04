"""Determine whether a fixture game should be included."""


def _should_include_fixture(
    last_ts: int,
    since_ms: int,
    until_ms: int | None,
) -> bool:
    if since_ms and last_ts <= since_ms:
        return False
    return not (until_ms is not None and last_ts >= until_ms)
