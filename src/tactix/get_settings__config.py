"""Load settings with environment overrides."""

from __future__ import annotations

import importlib
from typing import TYPE_CHECKING

from tactix.apply_env_user_overrides__config import _apply_env_user_overrides

if TYPE_CHECKING:
    from tactix.define_settings__config import Settings


def get_settings(source: str | None = None, profile: str | None = None) -> Settings:
    """Return a Settings instance for the given source/profile."""
    config_module = importlib.import_module("tactix.config")
    defaults_module = importlib.import_module("tactix.define_config_defaults__config")
    settings_module = importlib.import_module("tactix.define_settings__config")

    config_module.load_dotenv()
    importlib.reload(defaults_module)
    settings_module = importlib.reload(settings_module)

    settings = settings_module.Settings()
    _apply_env_user_overrides(settings)
    if source:
        settings.source = source
    settings.apply_source_defaults()
    settings.apply_lichess_profile(profile)
    settings.apply_chesscom_profile(profile)
    settings.ensure_dirs()
    return settings
