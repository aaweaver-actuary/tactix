from typing import Any


def _disabled_raw_pgn_summary() -> dict[str, Any]:
    return {
        "status": "disabled",
        "total_rows": 0,
        "distinct_games": 0,
        "latest_ingested_at": None,
        "sources": [],
    }
