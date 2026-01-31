from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

_MISSING = object()
_SETTINGS_ALIAS_FIELDS = (
    "lichess_user",
    "lichess_token",
    "lichess_oauth_client_id",
    "lichess_oauth_client_secret",
    "lichess_oauth_refresh_token",
    "lichess_oauth_token_url",
    "chesscom_user",
    "chesscom_token",
    "chesscom_time_class",
    "chesscom_profile",
    "chesscom_max_retries",
    "chesscom_retry_backoff_ms",
    "chesscom_checkpoint_path",
    "stockfish_path",
    "stockfish_checksum",
    "stockfish_checksum_mode",
    "stockfish_threads",
    "stockfish_hash_mb",
    "stockfish_movetime_ms",
    "stockfish_depth",
    "stockfish_multipv",
    "stockfish_skill_level",
    "stockfish_limit_strength",
    "stockfish_uci_elo",
    "stockfish_uci_analyse_mode",
    "stockfish_use_nnue",
    "stockfish_ponder",
    "stockfish_random_seed",
    "stockfish_max_retries",
    "stockfish_retry_backoff_ms",
)

# TODO: store this in the metadata db, not a random file
DEFAULT_DATA_DIR = Path(os.getenv("TACTIX_DATA_DIR", "data"))
DEFAULT_LICHESS_CHECKPOINT = DEFAULT_DATA_DIR / "lichess_since.txt"
DEFAULT_LICHESS_ANALYSIS_CHECKPOINT = DEFAULT_DATA_DIR / "analysis_checkpoint_lichess.json"
DEFAULT_LICHESS_FIXTURE = Path("tests/fixtures/lichess_rapid_sample.pgn")
DEFAULT_CHESSCOM_CHECKPOINT = DEFAULT_DATA_DIR / "chesscom_since.txt"
DEFAULT_CHESSCOM_ANALYSIS_CHECKPOINT = DEFAULT_DATA_DIR / "analysis_checkpoint_chesscom.json"
DEFAULT_CHESSCOM_FIXTURE = Path("tests/fixtures/chesscom_blitz_sample.pgn")
DEFAULT_BULLET_STOCKFISH_DEPTH = 8
DEFAULT_BLITZ_STOCKFISH_DEPTH = 10
DEFAULT_RAPID_STOCKFISH_DEPTH = 12
DEFAULT_CLASSICAL_STOCKFISH_DEPTH = 14
DEFAULT_CORRESPONDENCE_STOCKFISH_DEPTH = 16
_STOCKFISH_PROFILE_DEPTHS = {
    "bullet": DEFAULT_BULLET_STOCKFISH_DEPTH,
    "blitz": DEFAULT_BLITZ_STOCKFISH_DEPTH,
    "rapid": DEFAULT_RAPID_STOCKFISH_DEPTH,
    "classical": DEFAULT_CLASSICAL_STOCKFISH_DEPTH,
    "correspondence": DEFAULT_CORRESPONDENCE_STOCKFISH_DEPTH,
}
