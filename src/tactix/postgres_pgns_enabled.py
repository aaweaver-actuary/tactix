from tactix.config import Settings
from tactix.postgres_enabled import postgres_enabled


def postgres_pgns_enabled(settings: Settings) -> bool:
    return settings.postgres_pgns_enabled and postgres_enabled(settings)
