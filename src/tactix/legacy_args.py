"""Helpers for resolving legacy positional/keyword arguments."""

from __future__ import annotations

from typing import Any


def init_legacy_values(
    ordered_keys: tuple[str, ...],
    initial: dict[str, object] | None = None,
) -> dict[str, object]:
    """Initialize a values dictionary for legacy argument parsing."""
    values: dict[str, object] = dict.fromkeys(ordered_keys)
    if initial:
        values.update(initial)
    return values


def apply_legacy_kwargs(
    values: dict[str, object],
    ordered_keys: tuple[str, ...],
    legacy: dict[str, object],
) -> None:
    """Apply legacy keyword arguments into a values mapping."""
    for key in ordered_keys:
        if key in legacy:
            values[key] = legacy.pop(key)
    if legacy:
        raise TypeError(f"Unexpected keyword arguments: {', '.join(sorted(legacy))}")


def apply_legacy_args(
    values: dict[str, object],
    ordered_keys: tuple[str, ...],
    args: tuple[Any, ...],
) -> None:
    """Apply positional legacy arguments into a values mapping."""
    if not args:
        return
    if len(args) > len(ordered_keys):
        raise TypeError("Too many positional arguments")
    for key, value in zip(ordered_keys, args, strict=False):
        if values[key] is not None:
            raise TypeError(f"{key} provided multiple times")
        values[key] = value
