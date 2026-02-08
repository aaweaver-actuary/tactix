from tactix.FIXTURE_SPLIT_RE import FIXTURE_SPLIT_RE


def split_pgn_chunks(text: str) -> list[str]:
    """Takes a string containing one or more PGN games and splits it into individual PGN chunks."""
    if not text:
        return []
    return [chunk.strip() for chunk in FIXTURE_SPLIT_RE.split(text) if chunk.strip()]
