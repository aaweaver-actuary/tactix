"""Convenience exports for PGN parsing utilities."""

from __future__ import annotations

import time

import chess

from tactix._extract_site_id import _extract_site_id
from tactix.extract_game_id import extract_game_id
from tactix.extract_last_timestamp_ms import extract_last_timestamp_ms
from tactix.extract_pgn_metadata import extract_pgn_metadata
from tactix.latest_timestamp import latest_timestamp
from tactix.load_fixture_games import load_fixture_games
from tactix.normalize_pgn import normalize_pgn
from tactix.split_pgn_chunks import split_pgn_chunks

__all__ = [
    "_extract_site_id",
    "chess",
    "extract_game_id",
    "extract_last_timestamp_ms",
    "extract_pgn_metadata",
    "latest_timestamp",
    "load_fixture_games",
    "normalize_pgn",
    "split_pgn_chunks",
    "time",
]
