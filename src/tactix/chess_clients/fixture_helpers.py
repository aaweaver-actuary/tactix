from __future__ import annotations


def should_use_fixture_games(token: str | None, use_fixture_when_no_token: bool) -> bool:
    return bool(not token and use_fixture_when_no_token)
