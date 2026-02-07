"""Select hanging piece motifs for overrides."""

from tactix.analyze_tactics__positions import _OVERRIDEABLE_USER_MOTIFS


def _select_motif__hanging_piece_target(motif: str, best_motif: str | None) -> str:
    if motif == "hanging_piece":
        return "hanging_piece"
    if best_motif == "hanging_piece" and motif in _OVERRIDEABLE_USER_MOTIFS:
        return "hanging_piece"
    return ""
