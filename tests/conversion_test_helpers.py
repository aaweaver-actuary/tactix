"""Shared helpers for conversion unit tests."""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Any

from tactix.config import Settings
from tactix.db.duckdb_store import get_connection, init_schema
from tactix.db.position_repository_provider import insert_positions


def build_settings__chesscom_blitz_stockfish() -> Settings:
    settings = Settings(
        source="chesscom",
        chesscom_user="chesscom",
        chesscom_profile="blitz",
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        stockfish_movetime_ms=60,
        stockfish_depth=None,
        stockfish_multipv=1,
    )
    settings.apply_chesscom_profile("blitz")
    return settings


def create_connection__conversion(db_name: str):
    tmp_dir = Path(tempfile.mkdtemp())
    conn = get_connection(tmp_dir / db_name)
    init_schema(conn)
    return conn


def insert_position__single(conn, position: dict[str, Any]) -> dict[str, Any]:
    position_ids = insert_positions(conn, [position])
    position["position_id"] = position_ids[0]
    return position


def fetch_conversion__by_tactic_id(conn, tactic_id: int):
    return conn.execute(
        """
        SELECT converted, conversion_reason, result, user_uci
        FROM conversions
        WHERE opportunity_id = ?
        """,
        [tactic_id],
    ).fetchone()
