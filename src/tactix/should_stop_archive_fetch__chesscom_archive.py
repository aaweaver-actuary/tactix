def _should_stop_archive_fetch(since_ms: int, archive_max_ts: int) -> bool:
    return bool(since_ms and archive_max_ts and archive_max_ts <= since_ms)
