from dataclasses import dataclass


@dataclass(slots=True)
class PostgresStatus:
    enabled: bool
    status: str
    latency_ms: float | None = None
    error: str | None = None
    schema: str | None = None
    tables: list[str] | None = None
