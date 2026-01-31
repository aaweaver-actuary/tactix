from __future__ import annotations

from collections.abc import Mapping

from tactix.utils import to_int


def _pagination_values(data: Mapping[str, object]) -> tuple[int, int] | None:
    page = to_int(data.get("page") or data.get("current_page"))
    total_pages = to_int(data.get("total_pages") or data.get("totalPages"))
    if page is None or total_pages is None:
        return None
    return page, total_pages
