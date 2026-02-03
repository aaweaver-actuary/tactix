from typing import Any

import chess.engine

from tactix._configure_engine_options import _configure_engine_options
from tactix._filter_supported_options import _filter_supported_options


def _apply_engine_options(
    engine: chess.engine.SimpleEngine,
    options: dict[str, Any],
) -> dict[str, Any]:
    applied_options = _filter_supported_options(engine, options)
    return _configure_engine_options(engine, applied_options)
