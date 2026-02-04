"""Build a rating bucket SQL clause."""

from __future__ import annotations


def _rating_bucket_clause(bucket: str) -> str:
    """Return a SQL clause for filtering by rating bucket."""
    normalized = bucket.strip().lower()
    if normalized == "unknown":
        return "r.user_rating IS NULL"
    for resolver in (_resolve_lower_bucket, _resolve_range_bucket, _resolve_upper_bucket):
        clause = resolver(normalized)
        if clause is not None:
            return clause
    return "r.user_rating IS NULL"


def _resolve_lower_bucket(normalized: str) -> str | None:
    if not normalized.startswith("<"):
        return None
    value = normalized.lstrip("<").strip()
    if not value.isdigit():
        return None
    return f"r.user_rating IS NOT NULL AND r.user_rating < {int(value)}"


def _resolve_range_bucket(normalized: str) -> str | None:
    if "-" not in normalized:
        return None
    start, _, end = normalized.partition("-")
    start = start.strip()
    end = end.strip()
    if not (start.isdigit() and end.isdigit()):
        return None
    return f"r.user_rating >= {int(start)} AND r.user_rating <= {int(end)}"


def _resolve_upper_bucket(normalized: str) -> str | None:
    if not normalized.endswith("+"):
        return None
    lower = normalized.rstrip("+").strip()
    if not lower.isdigit():
        return None
    return f"r.user_rating >= {int(lower)}"
