"""Build PgnContext objects from user inputs."""

from tactix.pgn_context_kwargs import build_pgn_context_kwargs_from_values
from tactix.PgnContext import PgnContext


def _build_pgn_context(
    pgn: str | PgnContext,
    user: str | None = None,
    source: str | None = None,
    game_id: str | None = None,
    side_to_move_filter: str | None = None,
) -> PgnContext:
    """Return a PgnContext from user inputs."""
    if isinstance(pgn, PgnContext):
        return pgn
    if user is None or source is None:
        raise ValueError("user and source are required when pgn is a string")

    kwargs = build_pgn_context_kwargs_from_values(
        pgn,
        user,
        source,
        game_id,
        side_to_move_filter,
    )
    return PgnContext(**kwargs)
