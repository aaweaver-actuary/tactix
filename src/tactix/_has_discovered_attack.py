from tactix._has_discovered_line import (
    _has_discovered_line,
    build_discovered_line_context,
)
from tactix._has_new_target import _has_new_target
from tactix.DiscoveredAttackContext import DiscoveredAttackContext
from tactix.utils.logger import funclogger


@funclogger
def _has_discovered_attack(context: DiscoveredAttackContext) -> bool:
    return _has_discovered_line(
        build_discovered_line_context(context),
        predicate=lambda square: _has_new_target(
            context.detector,
            context.board_before,
            context.board_after,
            square,
            context.opponent,
        ),
    )
