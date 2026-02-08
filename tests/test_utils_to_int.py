"""Tests for to_int utility."""

from __future__ import annotations

from tactix.utils.to_int import to_int


def test_to_int_with_int() -> None:
    assert to_int(7) == 7


def test_to_int_with_str() -> None:
    assert to_int("42") == 42


def test_to_int_with_invalid_str() -> None:
    assert to_int("abc") is None


def test_to_int_with_other_type() -> None:
    assert to_int(3.14) is None
