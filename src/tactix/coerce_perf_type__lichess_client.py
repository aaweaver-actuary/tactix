from __future__ import annotations

from typing import cast

from berserk.types.common import PerfType

_PERF_TYPES: set[str] = {
    "ultraBullet",
    "bullet",
    "blitz",
    "rapid",
    "classical",
    "correspondence",
    "chess960",
    "kingOfTheHill",
    "threeCheck",
    "antichess",
    "atomic",
    "horde",
    "racingKings",
    "crazyhouse",
    "fromPosition",
}


def _coerce_perf_type(value: str | None) -> PerfType | None:
    """Coerce a string to a Lichess perf type.

    Args:
        value: Perf type string.

    Returns:
        Perf type if valid, otherwise None.
    """

    if not value:
        return None
    if value in _PERF_TYPES:
        return cast(PerfType, value)
    return None
