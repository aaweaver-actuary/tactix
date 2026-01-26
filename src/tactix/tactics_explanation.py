from __future__ import annotations

import chess


def format_tactic_explanation(
    fen: str | None, best_uci: str, motif: str | None
) -> tuple[str | None, str | None]:
    if not best_uci:
        return None, None
    best_san = None
    if fen:
        try:
            board = chess.Board(str(fen))
            move = chess.Move.from_uci(best_uci)
            if move in board.legal_moves:
                best_san = board.san(move)
        except Exception:  # noqa: BLE001
            best_san = None
    line = best_san or best_uci
    motif_label = motif or "tactic"
    explanation = f"{motif_label} tactic. Best line: {line}."
    return best_san, explanation
