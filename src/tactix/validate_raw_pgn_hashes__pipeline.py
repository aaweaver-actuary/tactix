from __future__ import annotations

from tactix.compute_pgn_hashes__pipeline import _compute_pgn_hashes
from tactix.count_hash_matches__pipeline import _count_hash_matches
from tactix.define_pipeline_state__pipeline import GameRow
from tactix.raise_for_hash_mismatch__pipeline import _raise_for_hash_mismatch


def _validate_raw_pgn_hashes(
    conn,
    rows: list[GameRow],
    source: str,
) -> dict[str, int]:
    if not rows:
        return {"computed": 0, "matched": 0}
    from tactix import pipeline as pipeline_module  # noqa: PLC0415

    computed = _compute_pgn_hashes(rows, source)
    stored = pipeline_module.fetch_latest_pgn_hashes(conn, list(computed.keys()), source)
    matched = _count_hash_matches(computed, stored)
    _raise_for_hash_mismatch(source, computed, stored, matched)
    return {"computed": len(computed), "matched": matched}
