from __future__ import annotations

import chess


def format_tactic_explanation(
    fen: str | None, best_uci: str, motif: str | None
) -> tuple[str | None, str | None]:
    if not best_uci:
        return None, None
    best_san = _best_san_from_fen(fen, best_uci)
    line = best_san or best_uci
    motif_label = motif or "tactic"
    explanation = f"{motif_label} tactic. Best line: {line}."
    return best_san, explanation


def _best_san_from_fen(fen: str | None, best_uci: str) -> str | None:
    if not fen:
        return None
    try:
        board = chess.Board(str(fen))
        move = chess.Move.from_uci(best_uci)
        return board.san(move) if move in board.legal_moves else None
    except Exception:
        return None
