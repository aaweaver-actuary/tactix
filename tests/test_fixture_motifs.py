import shutil
import unittest
from io import StringIO
from pathlib import Path

import chess
import chess.pgn

from tactix.config import Settings
from tactix.pgn_utils import extract_game_id, split_pgn_chunks
from tactix.StockfishEngine import StockfishEngine
from tactix.tactics_analyzer import analyze_position


def _fixture_positions(fixture_path: Path) -> list[dict[str, object]]:
    text = fixture_path.read_text().strip()
    if not text:
        return []
    positions: list[dict[str, object]] = []
    chunks = split_pgn_chunks(text)
    for idx, chunk in enumerate(chunks, start=1):
        game = chess.pgn.read_game(StringIO(chunk))
        if not game:
            continue
        fen = game.headers.get("FEN")
        board = chess.Board(fen) if fen else game.board()
        moves = list(game.mainline_moves())
        if not moves:
            continue
        move = moves[0]
        positions.append(
            {
                "game_id": extract_game_id(chunk),
                "position_id": idx,
                "fen": board.fen(),
                "uci": move.uci(),
            }
        )
    return positions


def _fixture_settings() -> Settings:
    return Settings(
        stockfish_path=Path(shutil.which("stockfish") or "stockfish"),
        stockfish_movetime_ms=80,
        stockfish_depth=12,
        stockfish_multipv=1,
        stockfish_random_seed=0,
    )


class FixtureMotifTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_fixture_mate_in_one(self) -> None:
        self._assert_fixture_motif("matein1.pgn", "mate", expected_mate_in=1)

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_fixture_mate_in_two(self) -> None:
        self._assert_fixture_motif("matein2.pgn", "mate", expected_mate_in=2)

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_fixture_hanging_piece(self) -> None:
        self._assert_fixture_motif("hangingpiece.pgn", "hanging_piece")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_fixture_fork(self) -> None:
        self._assert_fixture_motif("fork.pgn", "fork")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_fixture_pin(self) -> None:
        self._assert_fixture_motif("pin.pgn", "pin")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_fixture_skewer(self) -> None:
        self._assert_fixture_motif("skewer.pgn", "skewer")

    @unittest.skipUnless(shutil.which("stockfish"), "Stockfish binary not on PATH")
    def test_fixture_discovered_attack(self) -> None:
        self._assert_fixture_motif("discoveredattack.pgn", "discovered_attack")

    def _assert_fixture_motif(
        self,
        fixture_name: str,
        expected_motif: str,
        expected_mate_in: int | None = None,
    ) -> None:
        fixture_path = Path(__file__).resolve().parent / "fixtures" / fixture_name
        positions = _fixture_positions(fixture_path)
        if not positions:
            return
        settings = _fixture_settings()
        with StockfishEngine(settings) as engine:
            for position in positions:
                result = analyze_position(position, engine, settings=settings)
                self.assertIsNotNone(result)
                tactic_row, _ = result
                self.assertEqual(tactic_row["motif"], expected_motif)
                if expected_mate_in is not None:
                    self.assertEqual(tactic_row.get("mate_in"), expected_mate_in)
