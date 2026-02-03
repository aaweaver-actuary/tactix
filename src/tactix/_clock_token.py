from tactix.CLK_PATTERN import CLK_PATTERN


def _clock_token(comment: str) -> str | None:
    match = CLK_PATTERN.search(comment or "")
    if not match:
        return None
    return match.group(1)
