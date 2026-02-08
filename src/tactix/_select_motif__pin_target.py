"""Select the motif target for pin overrides."""


def _select_motif__pin_target(motif: str, best_motif: str | None) -> str:
    """Return the target motif for pin overrides."""
    if best_motif == "pin":
        return "pin"
    if motif == "pin":
        return "pin"
    return ""
