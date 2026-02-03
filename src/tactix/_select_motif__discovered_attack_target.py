def _select_motif__discovered_attack_target(motif: str, best_motif: str | None) -> str:
    if best_motif == "discovered_attack":
        return "discovered_attack"
    if motif == "discovered_attack":
        return "discovered_attack"
    return ""
