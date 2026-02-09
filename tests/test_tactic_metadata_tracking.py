import chess

from tactix.tactic_metadata import resolve_tactic_metadata


def test_resolve_tactic_metadata_detects_smothered_mate() -> None:
    metadata = resolve_tactic_metadata(
        "r1n5/5k2/2b2p1B/4p3/p1p1P3/Q1P3Pn/6BP/1R4RK b - - 0 43",
        "h3f2",
        "mate",
    )
    assert metadata["tactic_piece"] == "knight"
    assert metadata["mate_type"] == "smothered"


def test_resolve_tactic_metadata_detects_back_rank_mate() -> None:
    metadata = resolve_tactic_metadata(
        "6k1/8/8/8/8/8/4rPPP/6K1 b - - 0 1",
        "e2e1",
        "mate",
    )
    assert metadata["tactic_piece"] == "rook"
    assert metadata["mate_type"] == "back_rank"


def test_resolve_tactic_metadata_detects_dovetail_mate() -> None:
    metadata = resolve_tactic_metadata(
        "6qK/6PP/5k2/8/8/8/8/7k b - - 0 1",
        "g8g7",
        "mate",
    )
    assert metadata["tactic_piece"] == "queen"
    assert metadata["mate_type"] == "dovetail"


def test_resolve_tactic_metadata_detects_helper_piece_mate() -> None:
    metadata = resolve_tactic_metadata(
        "k7/8/8/8/5n2/6q1/8/7K b - - 0 1",
        "g3g2",
        "mate",
    )
    assert metadata["tactic_piece"] == "queen"
    assert metadata["mate_type"] == "helper_knight"


def test_resolve_tactic_metadata_tracks_piece_for_non_mate_tactic() -> None:
    metadata = resolve_tactic_metadata(chess.STARTING_FEN, "g1f3", "fork")
    assert metadata["tactic_piece"] == "knight"
    assert metadata["mate_type"] is None
