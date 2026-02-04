"""Fixture helpers for chess client tests."""

from __future__ import annotations


def should_use_fixture_games(token: str | None, use_fixture_when_no_token: bool) -> bool:
    """Return True when fixtures should be used in place of API calls."""
    return bool(not token and use_fixture_when_no_token)
