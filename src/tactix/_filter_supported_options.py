from typing import Any

import chess.engine


def _filter_supported_options(
    engine: chess.engine.SimpleEngine,
    options: dict[str, Any],
) -> dict[str, Any]:
    supported = getattr(engine, "options", {}) or {}
    return {name: value for name, value in options.items() if name in supported}
