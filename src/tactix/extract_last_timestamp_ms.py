import time
from io import StringIO

import chess.pgn

from tactix._parse_utc_start_ms import _parse_utc_start_ms


def extract_last_timestamp_ms(pgn: str) -> int:
    game = chess.pgn.read_game(StringIO(pgn))
    if not game:
        return int(time.time() * 1000)
    utc_date = game.headers.get("UTCDate")
    utc_time = game.headers.get("UTCTime")
    return _parse_utc_start_ms(utc_date, utc_time) or int(time.time() * 1000)
