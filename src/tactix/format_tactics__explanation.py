"""Format tactic explanations for UI/API payloads."""

from __future__ import annotations

from tactix._best_san_from_fen import _best_san_from_fen

_SAN_PIECE_LABELS = {
    "N": "knight",
    "B": "bishop",
    "R": "rook",
    "Q": "queen",
    "K": "king",
}


def _piece_label_from_san(san: str | None) -> str | None:
    if not san:
        return None
    if san.startswith("O-O"):
        return "king"
    return _SAN_PIECE_LABELS.get(san[0])


def format_tactic_explanation(
    fen: str | None, best_uci: str, motif: str | None
) -> tuple[str | None, str | None]:
    """Return a best SAN and explanation string for a tactic."""
    if not best_uci:
        return None, None
    best_san = _best_san_from_fen(fen, best_uci)
    line = best_san or best_uci
    piece_label = _piece_label_from_san(best_san)
    motif_label = motif or "tactic"
    if piece_label:
        explanation = f"{motif_label} tactic. Best line ({piece_label}): {line}."
    else:
        explanation = f"{motif_label} tactic. Best line: {line}."
    return best_san, explanation
