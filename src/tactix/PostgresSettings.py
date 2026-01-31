import os
from dataclasses import dataclass


@dataclass(slots=True)
class PostgresSettings:
    """PostgreSQL connection settings."""

    dsn: str | None = os.getenv("TACTIX_POSTGRES_DSN")
    host: str | None = os.getenv("TACTIX_POSTGRES_HOST")
    port: int = int(os.getenv("TACTIX_POSTGRES_PORT", "5432"))
    db: str | None = os.getenv("TACTIX_POSTGRES_DB")
    user: str | None = os.getenv("TACTIX_POSTGRES_USER")
    password: str | None = os.getenv("TACTIX_POSTGRES_PASSWORD")
    sslmode: str = os.getenv("TACTIX_POSTGRES_SSLMODE", "disable")
    connect_timeout_s: int = int(os.getenv("TACTIX_POSTGRES_CONNECT_TIMEOUT", "5"))
    analysis_enabled: bool = os.getenv("TACTIX_POSTGRES_ANALYSIS_ENABLED", "1") == "1"
    pgns_enabled: bool = os.getenv("TACTIX_POSTGRES_PGNS_ENABLED", "1") == "1"

    @property
    def is_configured(self) -> bool:
        """Check if sufficient settings are provided to connect.

        Returns:
            True if either DSN is provided or host, db, user, and password are set.
        """

        return self.dsn or all([self.host, self.db, self.user, self.password])
