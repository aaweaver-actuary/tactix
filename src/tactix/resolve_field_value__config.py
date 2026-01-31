from __future__ import annotations

from dataclasses import MISSING

from tactix.define_config_defaults__config import _MISSING


def _field_value(name: str, field_info: object, kwargs: dict[str, object]) -> object:
    value = kwargs.pop(name, _MISSING)
    if value is not _MISSING:
        return value
    default_factory = getattr(field_info, "default_factory", MISSING)
    if default_factory is not MISSING:
        return default_factory()
    default = getattr(field_info, "default", MISSING)
    if default is not MISSING:
        return default
    raise TypeError(f"Missing required argument: {name}")
