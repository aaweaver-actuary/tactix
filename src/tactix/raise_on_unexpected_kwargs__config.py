"""Raise on unexpected keyword arguments for settings."""

from __future__ import annotations


def _raise_on_unexpected_kwargs(kwargs: dict[str, object]) -> None:
    """Raise a TypeError when unexpected kwargs are provided."""
    if kwargs:
        unexpected = next(iter(kwargs))
        raise TypeError(f"Settings.__init__() got an unexpected keyword argument '{unexpected}'")
