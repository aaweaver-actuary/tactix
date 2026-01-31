from __future__ import annotations

from tactix.config import Settings, get_settings


def _build_pipeline_settings(
    settings: Settings | None,
    source: str | None = None,
    profile: str | None = None,
) -> Settings:
    settings = settings or get_settings(source=source, profile=profile)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    if profile is not None:
        settings.apply_lichess_profile(profile)
        settings.apply_chesscom_profile(profile)
    settings.ensure_dirs()
    return settings
