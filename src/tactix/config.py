from __future__ import annotations

from dotenv import load_dotenv

from tactix.apply_env_user_overrides__config import _apply_env_user_overrides
from tactix.apply_settings_aliases__config import _apply_settings_aliases
from tactix.define_chesscom_settings__config import ChesscomSettings
from tactix.define_config_defaults__config import (
    _MISSING,
    _SETTINGS_ALIAS_FIELDS,
    _STOCKFISH_PROFILE_DEPTHS,
    DEFAULT_BLITZ_STOCKFISH_DEPTH,
    DEFAULT_BULLET_STOCKFISH_DEPTH,
    DEFAULT_CHESSCOM_ANALYSIS_CHECKPOINT,
    DEFAULT_CHESSCOM_CHECKPOINT,
    DEFAULT_CHESSCOM_FIXTURE,
    DEFAULT_CLASSICAL_STOCKFISH_DEPTH,
    DEFAULT_CORRESPONDENCE_STOCKFISH_DEPTH,
    DEFAULT_DATA_DIR,
    DEFAULT_LICHESS_ANALYSIS_CHECKPOINT,
    DEFAULT_LICHESS_CHECKPOINT,
    DEFAULT_LICHESS_FIXTURE,
    DEFAULT_RAPID_STOCKFISH_DEPTH,
)
from tactix.define_lichess_settings__config import LichessSettings
from tactix.define_settings__config import Settings
from tactix.define_stockfish_settings__config import StockfishSettings
from tactix.get_settings__config import get_settings
from tactix.raise_on_unexpected_kwargs__config import _raise_on_unexpected_kwargs
from tactix.read_fork_severity_floor__config import _read_fork_severity_floor
from tactix.resolve_field_value__config import _field_value

load_dotenv()

__all__ = [
    "DEFAULT_BLITZ_STOCKFISH_DEPTH",
    "DEFAULT_BULLET_STOCKFISH_DEPTH",
    "DEFAULT_CHESSCOM_ANALYSIS_CHECKPOINT",
    "DEFAULT_CHESSCOM_CHECKPOINT",
    "DEFAULT_CHESSCOM_FIXTURE",
    "DEFAULT_CLASSICAL_STOCKFISH_DEPTH",
    "DEFAULT_CORRESPONDENCE_STOCKFISH_DEPTH",
    "DEFAULT_DATA_DIR",
    "DEFAULT_LICHESS_ANALYSIS_CHECKPOINT",
    "DEFAULT_LICHESS_CHECKPOINT",
    "DEFAULT_LICHESS_FIXTURE",
    "DEFAULT_RAPID_STOCKFISH_DEPTH",
    "_MISSING",
    "_SETTINGS_ALIAS_FIELDS",
    "_STOCKFISH_PROFILE_DEPTHS",
    "ChesscomSettings",
    "LichessSettings",
    "Settings",
    "StockfishSettings",
    "_apply_env_user_overrides",
    "_apply_settings_aliases",
    "_field_value",
    "_raise_on_unexpected_kwargs",
    "_read_fork_severity_floor",
    "get_settings",
]
