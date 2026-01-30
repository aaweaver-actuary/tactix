from datetime import UTC, datetime


def now() -> datetime:
    """Return the current UTC time."""

    return datetime.now(UTC)
