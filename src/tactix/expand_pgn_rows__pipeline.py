from __future__ import annotations

from tactix.config import Settings
from tactix.expand_single_pgn_row__pipeline import _expand_single_pgn_row
from tactix.GameRow import GameRow


def _expand_pgn_rows(rows: list[GameRow], settings: Settings) -> list[GameRow]:
    expanded: list[GameRow] = []
    for row in rows:
        expanded.extend(_expand_single_pgn_row(row, settings))
    return expanded
