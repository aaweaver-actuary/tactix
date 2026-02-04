"""Build fallback dependencies for position extraction."""

import os

from tactix._extract_positions_fallback import _extract_positions_fallback
from tactix._FallbackKwargs import _FallbackKwargs
from tactix.extractor_context import ExtractorDependencies
from tactix.position_extractor import _call_rust_extractor, _load_rust_extractor


def _fallback_kwargs() -> ExtractorDependencies:
    """Return extraction dependencies used for Rust fallback."""
    kwargs: _FallbackKwargs = {
        "getenv": os.getenv,
        "load_rust_extractor": _load_rust_extractor,
        "call_rust_extractor": _call_rust_extractor,
        "extract_positions_fallback": _extract_positions_fallback,
    }
    return ExtractorDependencies(**kwargs)
