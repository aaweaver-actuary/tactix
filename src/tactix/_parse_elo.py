"""Parse ELO values from PGN headers."""


def _parse_elo(raw: str | None) -> int | None:
    """Return the parsed ELO rating or None."""
    if not raw:
        return None
    try:
        return int(raw)
    except ValueError:
        return None
