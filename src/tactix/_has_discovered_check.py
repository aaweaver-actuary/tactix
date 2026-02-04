from tactix._has_discovered_line import (
    _has_discovered_line,
    build_discovered_line_context,
)
from tactix._is_discovered_check_slider import _is_discovered_check_slider
from tactix.DiscoveredCheckContext import DiscoveredCheckContext
from tactix.utils.logger import funclogger


@funclogger
def _has_discovered_check(context: DiscoveredCheckContext) -> bool:
    return _has_discovered_line(
        build_discovered_line_context(context),
        predicate=lambda square: _is_discovered_check_slider(
            context.board_before,
            context.board_after,
            square,
            context.king_square,
        ),
    )
