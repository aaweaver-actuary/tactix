"""Tests for config field value resolution."""

from __future__ import annotations

from dataclasses import MISSING, dataclass, field

import pytest

from tactix.resolve_field_value__config import _field_value


def test_field_value_uses_kwargs_value() -> None:
    kwargs: dict[str, object] = {"foo": 7}
    assert _field_value("foo", object(), kwargs) == 7
    assert "foo" not in kwargs


def test_field_value_uses_default_factory() -> None:
    @dataclass
    class Dummy:
        value: int = field(default_factory=lambda: 3)

    field_info = Dummy.__dataclass_fields__["value"]
    assert _field_value("value", field_info, {}) == 3

    class FactoryField:
        default_factory = staticmethod(lambda: 5)

    assert _field_value("value", FactoryField(), {}) == 5


def test_field_value_uses_default() -> None:
    @dataclass
    class Dummy:
        value: int = 4

    field_info = Dummy.__dataclass_fields__["value"]
    assert _field_value("value", field_info, {}) == 4

    class DefaultField:
        default_factory = MISSING
        default = 9

    assert _field_value("value", DefaultField(), {}) == 9


def test_field_value_missing_raises() -> None:
    @dataclass
    class Dummy:
        value: int

    field_info = Dummy.__dataclass_fields__["value"]
    with pytest.raises(TypeError, match="Missing required argument"):
        _field_value("value", field_info, {})
