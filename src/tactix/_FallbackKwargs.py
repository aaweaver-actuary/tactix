from collections.abc import Callable
from typing import TypedDict


class _FallbackKwargs(TypedDict):
    getenv: Callable[[str], str | None]
    load_rust_extractor: Callable[[], object | None]
    call_rust_extractor: Callable[
        [object, str, str, str, str | None, str | None],
        list[dict[str, object]],
    ]
    extract_positions_fallback: Callable[
        [str, str, str, str | None, str | None],
        list[dict[str, object]],
    ]
