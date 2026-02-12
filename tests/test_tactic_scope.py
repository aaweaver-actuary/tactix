import tactix.tactic_scope as scope


def test_scope_lists_are_consistent() -> None:
    assert scope.ALLOWED_MOTIFS == ("hanging_piece", "mate")
    assert set(scope.ALLOWED_MOTIFS).isdisjoint(scope.FUTURE_MOTIFS)
    assert set(scope.ALL_MOTIFS) == set(scope.ALLOWED_MOTIFS) | set(scope.FUTURE_MOTIFS)
    assert "initiative" not in scope.ALL_MOTIFS


def test_supported_motif_allows_mate_in_two() -> None:
    assert scope.is_supported_motif("hanging_piece")
    assert scope.is_supported_motif("mate", mate_in=1)
    assert scope.is_supported_motif("mate", mate_in=2)
    for motif in scope.FUTURE_MOTIFS:
        assert not scope.is_supported_motif(motif)


def test_scoped_motif_row_requires_mate_type() -> None:
    assert scope.is_scoped_motif_row("hanging_piece", None)
    assert scope.is_scoped_motif_row("mate", "back_rank")
    assert not scope.is_scoped_motif_row("mate", None)
    assert not scope.is_scoped_motif_row("pin", None)
