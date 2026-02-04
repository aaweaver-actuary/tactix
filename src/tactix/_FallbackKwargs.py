"""Legacy fallback kwargs typing for extractor dependencies."""

# pylint: disable=invalid-name

from collections.abc import Callable
from typing import TypedDict

from tactix.extractor_context import ExtractorRequest


class _FallbackKwargs(TypedDict):
    getenv: Callable[[str], str | None]
    load_rust_extractor: Callable[[], object | None]
    call_rust_extractor: Callable[[object, ExtractorRequest], list[dict[str, object]]]
    extract_positions_fallback: Callable[[ExtractorRequest], list[dict[str, object]]]
