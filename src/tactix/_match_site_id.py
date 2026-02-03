import re

from tactix.SITE_PATTERNS import SITE_PATTERNS


def _match_site_id(site: str) -> str | None:
    match = _match_site_patterns(site)
    if match is not None:
        return match
    return _fallback_site_id(site)


def _match_site_patterns(site: str) -> str | None:
    for pattern in SITE_PATTERNS:
        match = pattern.search(site)
        if match:
            return match.group(1)
    return None


def _fallback_site_id(site: str) -> str | None:
    if not site:
        return None
    sanitized = re.sub(r"[^A-Za-z0-9]+", "", site)
    if not sanitized or not _has_digits(sanitized):
        return None
    return sanitized[-16:]


def _has_digits(value: str) -> bool:
    return re.search(r"\d", value) is not None
