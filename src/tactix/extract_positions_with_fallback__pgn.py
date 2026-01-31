from __future__ import annotations

from collections.abc import Callable


def _extract_positions_with_fallback(
    pgn: str,
    user: str,
    source: str,
    game_id: str | None,
    side_to_move_filter: str | None,
    *,
    getenv: Callable[[str], str | None],
    load_rust_extractor: Callable[[], object | None],
    call_rust_extractor: Callable[
        [
            object,
            str,
            str,
            str,
            str | None,
            str | None,
        ],
        list[dict[str, object]],
    ],
    extract_positions_fallback: Callable[
        [str, str, str, str | None, str | None],
        list[dict[str, object]],
    ],
) -> list[dict[str, object]]:
    if getenv("PYTEST_CURRENT_TEST"):
        return extract_positions_fallback(
            pgn,
            user,
            source,
            game_id,
            side_to_move_filter,
        )
    rust_extractor = load_rust_extractor()
    if rust_extractor is None:
        return extract_positions_fallback(
            pgn,
            user,
            source,
            game_id,
            side_to_move_filter,
        )
    return call_rust_extractor(
        rust_extractor,
        pgn,
        user,
        source,
        game_id,
        side_to_move_filter,
    )
