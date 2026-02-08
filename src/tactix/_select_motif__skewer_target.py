"""Select the skewer target motif label."""


def _select_motif__skewer_target(motif: str, best_motif: str | None) -> str:
    if best_motif == "skewer":
        return "skewer"
    if motif == "skewer":
        return "skewer"
    return ""
