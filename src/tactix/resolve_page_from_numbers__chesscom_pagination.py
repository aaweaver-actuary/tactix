from __future__ import annotations

from tactix.build_page_url__chesscom_pagination import _page_url_for
from tactix.resolve_pagination_values__chesscom_pagination import _pagination_values


def _page_from_numbers(data: dict, current_url: str) -> str | None:
    """Compute a next page URL from numeric pagination fields.

    Args:
        data: Response payload.
        current_url: Current URL used for pagination.

    Returns:
        Next page URL if determinable.
    """

    page_info = _pagination_values(data)
    if page_info is None:
        return None
    page, total_pages = page_info
    if page >= total_pages:
        return None
    return _page_url_for(current_url, page + 1)
