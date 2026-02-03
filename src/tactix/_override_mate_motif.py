from tactix.analyze_tactics__positions import MATE_IN_ONE, MATE_IN_TWO


def _override_mate_motif(motif: str, mate_in: int | None) -> str:
    if mate_in == MATE_IN_TWO:
        return "mate"
    if mate_in == MATE_IN_ONE and motif != "hanging_piece":
        return "mate"
    return motif
