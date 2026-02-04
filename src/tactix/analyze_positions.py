"""Batch analysis helpers for chess positions."""

from collections.abc import Iterable

from tactix import analyze_tactics__positions as tactics_impl
from tactix.analyze_position import analyze_position
from tactix.config import Settings


def analyze_positions(
    positions: Iterable[dict[str, object]],
    settings: Settings,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    """Analyze a batch of positions and return tactics/outcomes rows."""
    tactics_rows: list[dict[str, object]] = []
    outcomes_rows: list[dict[str, object]] = []

    with tactics_impl.StockfishEngine(settings) as engine:
        for pos in positions:
            result = analyze_position(pos, engine, settings=settings)
            if result is None:
                continue
            tactic_row, outcome_row = result
            tactics_rows.append(tactic_row)
            outcomes_rows.append(outcome_row)
    return tactics_rows, outcomes_rows
