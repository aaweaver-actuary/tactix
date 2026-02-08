"""Helpers for extracting site ids from PGN headers."""

import re

SITE_PATTERNS = [
    re.compile(r"https?://lichess\.org/([A-Za-z0-9]+)"),
    re.compile(r"https?://(?:www\.)?chess\.com/game/(?:live|daily|archive|analysis)/([0-9]+)"),
    re.compile(r"https?://(?:www\.)?chess\.com/game/([0-9]+)"),
]


def _match_site_id(site: str) -> str | None:
    """Return a matched site id if available."""
    match = _match_site_patterns(site)
    if match is not None:
        return match
    return _fallback_site_id(site)


def _match_site_patterns(site: str) -> str | None:
    """Match site id using known patterns."""
    for pattern in SITE_PATTERNS:
        match = pattern.search(site)
        if match:
            return match.group(1)
    return None


def _fallback_site_id(site: str) -> str | None:
    """Fallback to a sanitized id from the site string."""
    if not site:
        return None
    sanitized = re.sub(r"[^A-Za-z0-9]+", "", site)
    if not sanitized or not _has_digits(sanitized):
        return None
    return sanitized[-16:]


def _has_digits(value: str) -> bool:
    """Return True when the value contains digits."""
    return re.search(r"\d", value) is not None
