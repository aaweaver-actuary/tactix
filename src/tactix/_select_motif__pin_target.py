def _select_motif__pin_target(motif: str, best_motif: str | None) -> str:
    if best_motif == "pin":
        return "pin"
    if motif == "pin":
        return "pin"
    return ""
