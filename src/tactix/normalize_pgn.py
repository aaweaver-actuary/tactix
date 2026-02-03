from io import StringIO

import chess.pgn


def normalize_pgn(pgn: str) -> str:
    game = chess.pgn.read_game(StringIO(pgn))
    if not game:
        return pgn.strip()
    exporter = chess.pgn.StringExporter(headers=True, variations=True, comments=True, columns=80)
    normalized = game.accept(exporter)
    return normalized.strip()
