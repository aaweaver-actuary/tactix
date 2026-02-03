from datetime import UTC, datetime


def _parse_utc_start_ms(utc_date: str | None, utc_time: str | None) -> int | None:
    if not utc_date or not utc_time:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y.%m.%d %H:%M:%S"):
        try:
            dt = datetime.strptime(f"{utc_date} {utc_time}", fmt).replace(tzinfo=UTC)
            return int(dt.timestamp() * 1000)
        except ValueError:
            continue
    return None
