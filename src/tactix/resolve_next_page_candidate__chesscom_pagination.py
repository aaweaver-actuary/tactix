"""Resolve a next page URL candidate from pagination payloads."""

from __future__ import annotations

from tactix.extract_candidate_href__chesscom_pagination import _extract_candidate_href


def _next_page_candidate(data: dict) -> str | None:
    for key in ("next_page", "next", "next_url", "nextPage"):
        href = _extract_candidate_href(data.get(key))
        if href:
            return href
    return None
