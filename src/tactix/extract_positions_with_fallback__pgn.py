"""Route extraction to Rust when available, otherwise use fallback."""

from __future__ import annotations

from tactix.extractor_context import ExtractorDependencies, ExtractorRequest


def _extract_positions_with_fallback(
    request: ExtractorRequest,
    deps: ExtractorDependencies,
) -> list[dict[str, object]]:
    if deps.getenv("PYTEST_CURRENT_TEST"):
        return deps.extract_positions_fallback(request)
    rust_extractor = deps.load_rust_extractor()
    if rust_extractor is None:
        return deps.extract_positions_fallback(request)
    return deps.call_rust_extractor(rust_extractor, request)
