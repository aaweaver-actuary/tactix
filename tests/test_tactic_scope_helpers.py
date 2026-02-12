from tactix import tactic_scope
from tactix.analyze_tactics__positions import MATE_IN_ONE, MATE_IN_TWO


def test_is_supported_motif_handles_none_and_hanging_piece() -> None:
    assert not tactic_scope.is_supported_motif(None)
    assert tactic_scope.is_supported_motif("hanging_piece")


def test_is_supported_motif_allows_mate_in_two() -> None:
    assert tactic_scope.is_supported_motif("mate", mate_in=MATE_IN_ONE)
    assert tactic_scope.is_supported_motif("mate", mate_in=MATE_IN_TWO)
    assert not tactic_scope.is_supported_motif("mate", mate_in=None)


def test_is_scoped_motif_row_requires_mate_type() -> None:
    assert not tactic_scope.is_scoped_motif_row(None, mate_type=None)
    assert not tactic_scope.is_scoped_motif_row("mate", mate_type=None)
    assert tactic_scope.is_scoped_motif_row("mate", mate_type="back_rank")


def test_is_allowed_motif_filter_accepts_none_and_allowed() -> None:
    assert tactic_scope.is_allowed_motif_filter(None)
    assert tactic_scope.is_allowed_motif_filter("mate")
    assert not tactic_scope.is_allowed_motif_filter("fork")


def test_allowed_motif_list_returns_allowed_tuple() -> None:
    assert tactic_scope.allowed_motif_list() == tactic_scope.ALLOWED_MOTIFS
