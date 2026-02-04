"""Tests for legacy args helpers."""

from __future__ import annotations

import pytest

from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values


def test_init_legacy_values_applies_initial() -> None:
    values = init_legacy_values(("a", "b"), {"b": 2})
    assert values == {"a": None, "b": 2}


def test_apply_legacy_kwargs_raises_on_unexpected() -> None:
    values = init_legacy_values(("a",))
    with pytest.raises(TypeError):
        apply_legacy_kwargs(values, ("a",), {"b": 1})


def test_apply_legacy_args_raises_on_too_many() -> None:
    values = init_legacy_values(("a",))
    with pytest.raises(TypeError):
        apply_legacy_args(values, ("a",), (1, 2))


def test_apply_legacy_args_raises_on_duplicate() -> None:
    values = init_legacy_values(("a",), {"a": 1})
    with pytest.raises(TypeError):
        apply_legacy_args(values, ("a",), (2,))
