"""Resolve fixture messages with defaults."""


def _resolve_fixture_message(message: str | None, default: str) -> str:
    """Return the message or a default value."""
    if message is None:
        return default
    return message
