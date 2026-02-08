from __future__ import annotations

from tactix.attach_position_ids__pipeline import _attach_position_ids
from tactix.config import Settings
from tactix.conversion_payload__pipeline import _conversion_payload
from tactix.db.position_repository_provider import insert_positions
from tactix.empty_conversion_payload__pipeline import _empty_conversion_payload
from tactix.extract_positions_for_rows__pipeline import _extract_positions_for_rows
from tactix.filter_positions_to_process__pipeline import _filter_positions_to_process
from tactix.prepare_raw_pgn_context__pipeline import _prepare_raw_pgn_context


def convert_raw_pgns_to_positions(
    settings: Settings | None = None,
    source: str | None = None,
    profile: str | None = None,
    limit: int | None = None,
) -> dict[str, object]:
    settings, conn, raw_pgns = _prepare_raw_pgn_context(
        settings=settings,
        source=source,
        profile=profile,
        limit=limit,
    )
    if not raw_pgns:
        return _empty_conversion_payload(settings)

    to_process = _filter_positions_to_process(conn, raw_pgns, settings)
    positions = _extract_positions_for_rows(to_process, settings)
    position_ids = insert_positions(conn, positions)
    _attach_position_ids(positions, position_ids)

    return _conversion_payload(settings, raw_pgns, to_process, positions)
