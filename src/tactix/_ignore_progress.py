"""No-op progress callback."""


def _ignore_progress(_payload: dict[str, object]) -> None:
    """Ignore progress payloads."""
    return
