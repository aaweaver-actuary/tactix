"""Shared helpers for building PGN context keyword arguments."""

from __future__ import annotations

from dataclasses import dataclass

from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values
from tactix.PgnContextKwargs import PgnContextKwargs

_PGN_CONTEXT_KEYS = (
    "pgn",
    "user",
    "source",
    "game_id",
    "side_to_move_filter",
)


@dataclass(frozen=True)
class PgnContextInputs:
    """Grouped inputs for PGN context helpers."""

    pgn: str
    user: str
    source: str
    game_id: str | None = None
    side_to_move_filter: str | None = None


def build_pgn_context_inputs_from_values(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> PgnContextInputs:
    """Build PgnContextInputs from raw values."""
    return PgnContextInputs(
        pgn=pgn,
        user=user,
        source=source,
        game_id=game_id,
        side_to_move_filter=side_to_move_filter,
    )


def build_pgn_context_kwargs_from_values(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> PgnContextKwargs:
    """Build PGN context kwargs from raw values."""
    return build_pgn_context_kwargs(
        inputs=build_pgn_context_inputs_from_values(
            pgn,
            user,
            source,
            game_id=game_id,
            side_to_move_filter=side_to_move_filter,
        )
    )


def build_pgn_context_kwargs(
    *args: object,
    inputs: PgnContextInputs | None = None,
    **legacy: object,
) -> PgnContextKwargs:
    """Return a keyword argument dict for PGN-derived contexts."""
    if inputs is None:
        values = init_legacy_values(_PGN_CONTEXT_KEYS)
    else:
        values = init_legacy_values(
            _PGN_CONTEXT_KEYS,
            initial={
                "pgn": inputs.pgn,
                "user": inputs.user,
                "source": inputs.source,
                "game_id": inputs.game_id,
                "side_to_move_filter": inputs.side_to_move_filter,
            },
        )
    apply_legacy_kwargs(values, _PGN_CONTEXT_KEYS, legacy)
    apply_legacy_args(values, _PGN_CONTEXT_KEYS, args)
    return PgnContextKwargs(
        pgn=values["pgn"],
        user=values["user"],
        source=values["source"],
        game_id=values["game_id"],
        side_to_move_filter=values["side_to_move_filter"],
    )
