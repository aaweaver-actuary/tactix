from unittest.mock import MagicMock

from tactix._list_tables import _list_tables
from tactix._resolve_chesscom_profile_value import _resolve_chesscom_profile_value
from tactix._resolve_profile_value__settings import _resolve_profile_value__settings
from tactix.config import Settings


def test_resolve_chesscom_profile_value_prefers_profile() -> None:
    settings = Settings()
    settings.chesscom_profile = "blitz"
    settings.chesscom.time_class = "rapid"
    assert _resolve_chesscom_profile_value(settings) == "blitz"


def test_resolve_chesscom_profile_value_maps_daily() -> None:
    settings = Settings()
    settings.chesscom_profile = None
    settings.chesscom.time_class = "daily"
    assert _resolve_chesscom_profile_value(settings) == "correspondence"


def test_resolve_profile_value_settings_uses_chesscom_path() -> None:
    settings = Settings()
    settings.source = "chesscom"
    settings.chesscom_profile = "bullet"
    assert _resolve_profile_value__settings(settings) == "bullet"


def test_resolve_profile_value_settings_falls_back_to_lichess() -> None:
    settings = Settings()
    settings.source = "lichess"
    settings.lichess_profile = "blitz"
    settings.rapid_perf = "rapid"
    assert _resolve_profile_value__settings(settings) == "blitz"


def test_list_tables_returns_sorted_table_names() -> None:
    conn = MagicMock()
    cursor = MagicMock()
    cursor.__enter__.return_value = cursor
    cursor.fetchall.return_value = [("games",), ("positions",)]
    conn.cursor.return_value = cursor

    result = _list_tables(conn, "tactix")

    cursor.execute.assert_called_once()
    assert result == ["games", "positions"]
