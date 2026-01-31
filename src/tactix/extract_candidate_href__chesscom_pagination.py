from __future__ import annotations

from collections.abc import Mapping
from typing import cast

from tactix.ensure_non_empty_str__chesscom_pagination import _non_empty_str
from tactix.get_first_string__chesscom_pagination import _first_string


def _extract_candidate_href(candidate: object) -> str | None:
    if isinstance(candidate, str):
        return _non_empty_str(candidate)
    if isinstance(candidate, Mapping):
        candidate_map = cast(Mapping[str, object], candidate)
        return _first_string(candidate_map, ("href", "url"))
    return None
