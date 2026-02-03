from __future__ import annotations

from tactix._best_san_from_fen import _best_san_from_fen


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
