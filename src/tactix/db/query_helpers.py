"""Shared helpers for SQL query assembly."""


def apply_limit_clause(params: list[object], limit: int | None) -> str:
    """Append a LIMIT clause and bind parameter when requested."""
    if limit is None:
        return ""
    params.append(int(limit))
    return "LIMIT ?"
