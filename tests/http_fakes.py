from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

import requests

from tactix.pgn_utils import latest_timestamp


@dataclass(slots=True)
class FakeResponse:
    status_code: int = 200
    json_data: dict | None = None
    headers: dict | None = None

    def json(self) -> dict:
        return self.json_data or {}

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code} Error")


def make_fake_get(
    responses: Iterable[FakeResponse],
    *,
    captured_urls: list[str] | None = None,
) -> Callable[..., FakeResponse]:
    queue = list(responses)

    def _fake_get(url: str, *_args, **_kwargs) -> FakeResponse:
        if captured_urls is not None:
            captured_urls.append(url)
        return queue.pop(0)

    return _fake_get


def assert_fixture_games_have_timestamps(
    games: list[dict],
    *,
    min_games: int = 1,
) -> int:
    assert len(games) >= min_games
    last_ts = latest_timestamp(games)
    assert last_ts > 0
    return last_ts
