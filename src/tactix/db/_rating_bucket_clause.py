"""Build a rating bucket SQL clause."""

from __future__ import annotations


def _rating_bucket_clause(bucket: str) -> str:
    """Return a SQL clause for filtering by rating bucket."""
    normalized = bucket.strip().lower()
    if normalized == "unknown":
        return "r.user_rating IS NULL"
    if normalized.startswith("<"):
        value = normalized.lstrip("<").strip()
        if value.isdigit():
            return f"r.user_rating IS NOT NULL AND r.user_rating < {int(value)}"
    if "-" in normalized:
        start, _, end = normalized.partition("-")
        start = start.strip()
        end = end.strip()
        if start.isdigit() and end.isdigit():
            return f"r.user_rating >= {int(start)} AND r.user_rating <= {int(end)}"
    if normalized.endswith("+"):
        lower = normalized.rstrip("+").strip()
        if lower.isdigit():
            return f"r.user_rating >= {int(lower)}"
    return "r.user_rating IS NULL"
