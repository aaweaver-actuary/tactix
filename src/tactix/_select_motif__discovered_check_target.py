"""Select the motif target for discovered check overrides."""


def _select_motif__discovered_check_target(motif: str, best_motif: str | None) -> str:
    """Return the target motif for discovered check overrides."""
    if best_motif == "discovered_check":
        return "discovered_check"
    if motif == "discovered_check":
        return "discovered_check"
    return ""
