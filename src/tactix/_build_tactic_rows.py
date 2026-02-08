"""Build tactic and outcome row dicts from analysis inputs."""

from __future__ import annotations

from dataclasses import asdict

from tactix.OutcomeRow import OutcomeRow
from tactix.TacticRow import TacticRow
from tactix.TacticRowInput import TacticRowInput


def _build_tactic_rows(inputs: TacticRowInput) -> tuple[dict[str, object], dict[str, object]]:
    """Return tactic and outcome row mappings for storage."""
    tactic_row = TacticRow.from_inputs(inputs).to_row()
    outcome_row = asdict(OutcomeRow.from_inputs(inputs))
    return tactic_row, outcome_row
