import chess.pgn

from tactix._match_site_id import _match_site_id


def _extract_site_id(game: chess.pgn.Game | None) -> str | None:
    if not game:
        return None
    site = game.headers.get("Site", "")
    return _match_site_id(site)
