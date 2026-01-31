from __future__ import annotations

from typing import TYPE_CHECKING

from tactix.define_config_defaults__config import _MISSING, _SETTINGS_ALIAS_FIELDS

if TYPE_CHECKING:
    from tactix.define_settings__config import Settings


def _apply_settings_aliases(settings: Settings, kwargs: dict[str, object]) -> None:
    for alias in _SETTINGS_ALIAS_FIELDS:
        value = kwargs.pop(alias, _MISSING)
        if value is not _MISSING:
            setattr(settings, alias, value)
