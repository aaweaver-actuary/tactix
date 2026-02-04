"""Attach position ids to extracted positions."""

from __future__ import annotations


def _attach_position_ids(
    positions: list[dict[str, object]],
    position_ids: list[int],
) -> None:
    """Mutate positions to include their corresponding ids."""
    for pos, pos_id in zip(positions, position_ids, strict=False):
        pos["position_id"] = pos_id
