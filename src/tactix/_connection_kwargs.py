"""Build Postgres connection keyword arguments."""

from typing import Any

from tactix.config import Settings


def _connection_kwargs(settings: Settings) -> dict[str, Any] | None:
    if settings.postgres_dsn:
        return {"dsn": settings.postgres_dsn}
    if not settings.postgres_host or not settings.postgres_db:
        return None
    return {
        "host": settings.postgres_host,
        "port": settings.postgres_port,
        "dbname": settings.postgres_db,
        "user": settings.postgres_user,
        "password": settings.postgres_password,
        "sslmode": settings.postgres_sslmode,
        "connect_timeout": settings.postgres_connect_timeout_s,
    }
