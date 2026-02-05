from tactix.analyze_tactics__positions import MATE_IN_ONE, MATE_IN_TWO


def _resolve_mate_in(mate_in_one: bool, mate_in_two: bool) -> int | None:
    if mate_in_two:
        return MATE_IN_TWO
    if mate_in_one:
        return MATE_IN_ONE
    return None


_VULTURE_USED = (_resolve_mate_in,)
