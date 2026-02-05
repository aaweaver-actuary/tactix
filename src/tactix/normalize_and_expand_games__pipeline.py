from __future__ import annotations

from collections.abc import Mapping

from tactix.config import Settings
from tactix.dedupe_games__pipeline import _dedupe_games
from tactix.expand_pgn_rows__pipeline import _expand_pgn_rows
from tactix.GameRow import GameRow
from tactix.normalize_game_row__pipeline import _normalize_game_row


def _normalize_and_expand_games(
    raw_games: list[Mapping[str, object]],
    settings: Settings,
) -> list[GameRow]:
    games = [_normalize_game_row(game, settings) for game in raw_games]
    games = _expand_pgn_rows(games, settings)
    return _dedupe_games(games)
