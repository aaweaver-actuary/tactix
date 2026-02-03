from datetime import UTC, datetime


class Now:
    @staticmethod
    def as_datetime() -> datetime:
        """Return the current UTC time as a datetime object."""

        return datetime.now(UTC)

    @staticmethod
    def as_dt() -> datetime:
        """Return the current UTC time as a datetime object. Alias for as_datetime()."""

        return datetime.now(UTC)

    @staticmethod
    def as_seconds(as_int: bool = False) -> float:
        """Return the current UTC time as a float timestamp in seconds."""

        if as_int:
            return int(datetime.now(UTC).timestamp())
        return datetime.now(UTC).timestamp()

    @staticmethod
    def as_milliseconds() -> int:
        """Return the current UTC time as an integer timestamp in milliseconds."""

        return int(datetime.now(UTC).timestamp() * 1000)

    @staticmethod
    def to_utc(dt: datetime | None) -> datetime | None:
        """Convert a datetime object to UTC timezone."""

        try:
            if dt is None:
                return None
            if dt.tzinfo is None:
                return dt.replace(tzinfo=UTC)
            return dt.astimezone(UTC)
        except Exception:
            return None


_VULTURE_USED = (Now.as_dt, Now.as_seconds, Now.as_milliseconds)
