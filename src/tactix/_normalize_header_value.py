def _normalize_header_value(value: str | None) -> str | None:
    if not value:
        return None
    if value.strip() == "?":
        return None
    return value
