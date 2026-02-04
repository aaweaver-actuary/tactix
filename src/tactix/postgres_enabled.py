"""Check whether Postgres is enabled by configuration."""

from tactix._connection_kwargs import _connection_kwargs
from tactix.config import Settings


def postgres_enabled(settings: Settings) -> bool:
    """Return True when Postgres settings are configured."""
    return _connection_kwargs(settings) is not None
