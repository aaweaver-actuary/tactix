from collections.abc import Iterable, Mapping
from typing import Any


def coerce_raw_pgn_summary_rows(
    rows: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    return [dict(row) for row in rows]
