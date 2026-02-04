"""Pagination helper to resolve Chess.com next page URLs."""

from __future__ import annotations

from tactix.resolve_next_page_candidate__chesscom_pagination import _next_page_candidate
from tactix.resolve_page_from_numbers__chesscom_pagination import _page_from_numbers


def _next_page_url(data: dict, current_url: str) -> str | None:
    """Resolve the next page URL from a response payload.

    Args:
        data: Response payload.
        current_url: Current URL used for pagination.

    Returns:
        Next page URL if available.
    """

    candidate = _next_page_candidate(data)
    return candidate or _page_from_numbers(data, current_url)
