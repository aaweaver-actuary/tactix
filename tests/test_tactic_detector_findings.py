import chess
import pytest

from tactix.CaptureDetector import CaptureDetector
from tactix.DiscoveredAttackDetector import DiscoveredAttackDetector
from tactix.DiscoveredCheckDetector import DiscoveredCheckDetector
from tactix.ForkDetector import ForkDetector
from tactix.HangingPieceDetector import HangingPieceDetector
from tactix.PinDetector import PinDetector
from tactix.SkewerDetector import SkewerDetector
from tactix.TacticContext import TacticContext
from tactix.TacticDetectionService import TacticDetectionService
from tactix.detect_tactics__motifs import CheckDetector, EscapeDetector, MateDetector
from tactix.tactic_scope import is_supported_motif
from tests.fixture_helpers import hanging_piece_fixture_position


def _context_from_move(board: chess.Board, move: chess.Move) -> TacticContext:
    board_before = board.copy()
    board_after = board.copy()
    board_after.push(move)
    return TacticContext(
        board_before=board_before,
        board_after=board_after,
        best_move=move,
        mover_color=board_before.turn,
    )


def _assert_finding(detector, context: TacticContext, motif: str) -> None:
    findings = detector.detect(context)
    assert [finding.motif for finding in findings] == [motif]


def _legacy_findings(context: TacticContext) -> list[str]:
    detectors = [
        MateDetector(),
        DiscoveredAttackDetector(),
        SkewerDetector(),
        PinDetector(),
        ForkDetector(),
        DiscoveredCheckDetector(),
        HangingPieceDetector(),
        CaptureDetector(),
        CheckDetector(),
        EscapeDetector(),
    ]
    seen: set[str] = set()
    motifs: list[str] = []
    for detector in detectors:
        for finding in detector.detect(context):
            if finding.motif in seen:
                continue
            seen.add(finding.motif)
            motifs.append(finding.motif)
    return motifs


def test_mate_detector_returns_finding() -> None:
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.G6, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.H6, chess.Piece(chess.QUEEN, chess.WHITE))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("h6g7")
    context = _context_from_move(board, move)

    _assert_finding(MateDetector(), context, "mate")


def test_check_detector_returns_finding() -> None:
    if not is_supported_motif("check"):
        pytest.skip("Check motif disabled in current scope")
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.H5, chess.Piece(chess.QUEEN, chess.WHITE))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("h5e5")
    context = _context_from_move(board, move)

    _assert_finding(CheckDetector(), context, "check")


def test_escape_detector_returns_finding() -> None:
    if not is_supported_motif("escape"):
        pytest.skip("Escape motif disabled in current scope")
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.G4, chess.Piece(chess.BISHOP, chess.BLACK))
    board.set_piece_at(chess.F3, chess.Piece(chess.KNIGHT, chess.WHITE))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("f3e5")
    context = _context_from_move(board, move)

    _assert_finding(EscapeDetector(), context, "escape")


def test_capture_detector_returns_finding() -> None:
    if not is_supported_motif("capture"):
        pytest.skip("Capture motif disabled in current scope")
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.E4, chess.Piece(chess.PAWN, chess.WHITE))
    board.set_piece_at(chess.D5, chess.Piece(chess.PAWN, chess.BLACK))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("e4d5")
    context = _context_from_move(board, move)

    _assert_finding(CaptureDetector(), context, "capture")


def test_hanging_piece_detector_returns_finding() -> None:
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.H1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.C4, chess.Piece(chess.BISHOP, chess.WHITE))
    board.set_piece_at(chess.E6, chess.Piece(chess.ROOK, chess.BLACK))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("c4e6")
    context = _context_from_move(board, move)

    _assert_finding(HangingPieceDetector(), context, "hanging_piece")


def test_fork_detector_returns_finding() -> None:
    if not is_supported_motif("fork"):
        pytest.skip("Fork motif disabled in current scope")
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.F5, chess.Piece(chess.KNIGHT, chess.WHITE))
    board.set_piece_at(chess.E8, chess.Piece(chess.QUEEN, chess.BLACK))
    board.set_piece_at(chess.F7, chess.Piece(chess.ROOK, chess.BLACK))
    board.set_piece_at(chess.A1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("f5d6")
    context = _context_from_move(board, move)

    _assert_finding(ForkDetector(), context, "fork")


def test_pin_detector_returns_finding() -> None:
    if not is_supported_motif("pin"):
        pytest.skip("Pin motif disabled in current scope")
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.E8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.C6, chess.Piece(chess.KNIGHT, chess.BLACK))
    board.set_piece_at(chess.F1, chess.Piece(chess.BISHOP, chess.WHITE))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("f1b5")
    context = _context_from_move(board, move)

    _assert_finding(PinDetector(), context, "pin")


def test_skewer_detector_returns_finding() -> None:
    if not is_supported_motif("skewer"):
        pytest.skip("Skewer motif disabled in current scope")
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.G1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.E7, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.E8, chess.Piece(chess.QUEEN, chess.BLACK))
    board.set_piece_at(chess.E2, chess.Piece(chess.ROOK, chess.WHITE))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("e2e1")
    context = _context_from_move(board, move)

    _assert_finding(SkewerDetector(), context, "skewer")


def test_discovered_attack_detector_returns_finding() -> None:
    if not is_supported_motif("discovered_attack"):
        pytest.skip("Discovered attack disabled in current scope")
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.H8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
    board.set_piece_at(chess.A2, chess.Piece(chess.BISHOP, chess.WHITE))
    board.set_piece_at(chess.A8, chess.Piece(chess.QUEEN, chess.BLACK))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("a2b1")
    context = _context_from_move(board, move)

    _assert_finding(DiscoveredAttackDetector(), context, "discovered_attack")


def test_discovered_check_detector_returns_finding() -> None:
    if not is_supported_motif("discovered_check"):
        pytest.skip("Discovered check disabled in current scope")
    board = chess.Board(None)
    board.clear()
    board.set_piece_at(chess.E1, chess.Piece(chess.KING, chess.WHITE))
    board.set_piece_at(chess.A8, chess.Piece(chess.KING, chess.BLACK))
    board.set_piece_at(chess.A1, chess.Piece(chess.ROOK, chess.WHITE))
    board.set_piece_at(chess.A2, chess.Piece(chess.BISHOP, chess.WHITE))
    board.turn = chess.WHITE

    move = chess.Move.from_uci("a2b1")
    context = _context_from_move(board, move)

    _assert_finding(DiscoveredCheckDetector(), context, "discovered_check")


def test_tactic_detection_service_matches_legacy_detection() -> None:
    positions = [hanging_piece_fixture_position()]

    detectors = [
        MateDetector(),
        DiscoveredAttackDetector(),
        SkewerDetector(),
        PinDetector(),
        ForkDetector(),
        DiscoveredCheckDetector(),
        HangingPieceDetector(),
        CaptureDetector(),
        CheckDetector(),
        EscapeDetector(),
    ]
    service = TacticDetectionService(detectors)

    for position in positions:
        board = chess.Board(str(position["fen"]))
        move = chess.Move.from_uci(str(position["uci"]))
        context = _context_from_move(board, move)
        service_motifs = [finding.motif for finding in service.detect(context)]
        legacy_motifs = _legacy_findings(context)
        assert service_motifs == legacy_motifs
