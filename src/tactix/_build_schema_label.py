from tactix.ANALYSIS_SCHEMA import ANALYSIS_SCHEMA
from tactix.config import Settings
from tactix.PGN_SCHEMA import PGN_SCHEMA


def _build_schema_label(settings: Settings) -> str:
    schema_label = "tactix_ops"
    if settings.postgres_analysis_enabled:
        schema_label = f"{schema_label},{ANALYSIS_SCHEMA}"
    if settings.postgres_pgns_enabled:
        schema_label = f"{schema_label},{PGN_SCHEMA}"
    return schema_label
