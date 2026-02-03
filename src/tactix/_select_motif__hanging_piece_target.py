def _select_motif__hanging_piece_target(motif: str, best_motif: str | None) -> str:
    if best_motif == "hanging_piece":
        return "hanging_piece"
    if motif == "hanging_piece":
        return "hanging_piece"
    return ""
