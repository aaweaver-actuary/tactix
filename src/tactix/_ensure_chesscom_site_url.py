from io import StringIO

import chess.pgn

from tactix.extract_game_id import extract_game_id


def _ensure_chesscom_site_url(pgn: str) -> str:
    game = chess.pgn.read_game(StringIO(pgn))
    if not game:
        return pgn
    site = (game.headers.get("Site") or "").lower()
    if "chess.com" in site and "chess.com/game/live/" not in site:
        game_id = extract_game_id(pgn)
        game.headers["Site"] = f"https://chess.com/game/live/{game_id}"
        exporter = chess.pgn.StringExporter(
            headers=True,
            variations=True,
            comments=True,
            columns=80,
        )
        return game.accept(exporter).strip()
    return pgn
