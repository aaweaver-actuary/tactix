from tactix._fetch_latest_pgn_metadata import _fetch_latest_pgn_metadata


def _latest_pgn_metadata(
    cur,
    key: tuple[str, str],
    latest_cache: dict[tuple[str, str], tuple[str | None, int]],
) -> tuple[str | None, int]:
    cached = latest_cache.get(key)
    if cached is not None:
        return cached
    latest_hash, latest_version = _fetch_latest_pgn_metadata(cur, key[0], key[1])
    latest_cache[key] = (latest_hash, latest_version)
    return latest_hash, latest_version
