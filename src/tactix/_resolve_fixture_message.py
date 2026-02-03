def _resolve_fixture_message(message: str | None, default: str) -> str:
    if message is None:
        return default
    return message
