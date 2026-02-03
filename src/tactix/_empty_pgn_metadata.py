def _empty_pgn_metadata() -> dict[str, object]:
    return {
        "user_rating": None,
        "time_control": None,
        "white_player": None,
        "black_player": None,
        "white_elo": None,
        "black_elo": None,
        "result": None,
        "event": None,
        "site": None,
        "utc_date": None,
        "utc_time": None,
        "termination": None,
        "start_timestamp_ms": None,
    }
