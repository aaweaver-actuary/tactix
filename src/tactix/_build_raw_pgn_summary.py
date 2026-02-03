from collections.abc import Mapping
from typing import Any

from tactix.db.raw_pgn_summary import build_raw_pgn_summary_payload


def _build_raw_pgn_summary(
    sources: list[Mapping[str, Any]], totals: Mapping[str, Any]
) -> dict[str, Any]:
    return build_raw_pgn_summary_payload(sources=sources, totals=totals)
