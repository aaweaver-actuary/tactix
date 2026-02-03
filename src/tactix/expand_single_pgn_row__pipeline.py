from __future__ import annotations

from tactix.build_chunk_row__pipeline import _build_chunk_row
from tactix.config import Settings
from tactix.define_pipeline_state__pipeline import SINGLE_PGN_CHUNK, GameRow
from tactix.split_pgn_chunks import split_pgn_chunks


def _expand_single_pgn_row(row: GameRow, settings: Settings) -> list[GameRow]:
    pgn_text = row.get("pgn", "")
    chunks = split_pgn_chunks(pgn_text)
    if len(chunks) <= SINGLE_PGN_CHUNK:
        return [row]
    return [_build_chunk_row(row, chunk, settings) for chunk in chunks]
