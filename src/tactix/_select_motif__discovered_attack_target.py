"""Select the motif target for discovered attack overrides."""


def _select_motif__discovered_attack_target(motif: str, best_motif: str | None) -> str:
    """Return the target motif for discovered attack overrides."""
    if best_motif == "discovered_attack":
        return "discovered_attack"
    if motif == "discovered_attack":
        return "discovered_attack"
    return ""
