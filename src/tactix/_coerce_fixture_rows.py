from collections.abc import Callable, Iterable


def _coerce_fixture_rows(
    games: list[dict[str, object]],
    coerce_rows: Callable[[Iterable[dict[str, object]]], list[dict]] | None,
) -> list[dict[str, object]]:
    if coerce_rows is None:
        return games
    return coerce_rows(games)
