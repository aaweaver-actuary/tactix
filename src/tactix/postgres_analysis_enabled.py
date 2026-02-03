from tactix.config import Settings
from tactix.postgres_enabled import postgres_enabled


def postgres_analysis_enabled(settings: Settings) -> bool:
    return settings.postgres_analysis_enabled and postgres_enabled(settings)
