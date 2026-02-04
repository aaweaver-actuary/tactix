"""Build chess.com pagination URLs."""

from __future__ import annotations

from urllib.parse import parse_qs, urlencode, urlparse, urlunparse


def _page_url_for(current_url: str, page: int) -> str:
    parsed = urlparse(current_url)
    query = parse_qs(parsed.query)
    query["page"] = [str(page)]
    return urlunparse(parsed._replace(query=urlencode(query, doseq=True)))
