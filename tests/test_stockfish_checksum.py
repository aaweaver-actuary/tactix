import hashlib
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import chess
import chess.engine
import pytest

from tactix.config import Settings
from tactix.stockfish_runner import StockfishEngine, verify_stockfish_checksum


def _sha256_for_bytes(payload: bytes) -> str:
    digest = hashlib.sha256()
    digest.update(payload)
    return digest.hexdigest()


def test_stockfish_checksum_matches(tmp_path: Path) -> None:
    payload = b"fake-stockfish-binary"
    binary_path = tmp_path / "stockfish"
    binary_path.write_bytes(payload)
    expected = _sha256_for_bytes(payload)

    assert verify_stockfish_checksum(binary_path, expected, mode="enforce") is True


def test_stockfish_checksum_mismatch_enforced(tmp_path: Path) -> None:
    binary_path = tmp_path / "stockfish"
    binary_path.write_bytes(b"different-binary")
    expected = _sha256_for_bytes(b"expected-content")

    with pytest.raises(RuntimeError, match="Stockfish checksum mismatch"):
        verify_stockfish_checksum(binary_path, expected, mode="enforce")


def test_stockfish_checksum_mismatch_warn(tmp_path: Path) -> None:
    binary_path = tmp_path / "stockfish"
    binary_path.write_bytes(b"different-binary")
    expected = _sha256_for_bytes(b"expected-content")

    assert verify_stockfish_checksum(binary_path, expected, mode="warn") is False


def test_analyse_fallback_material_score() -> None:
    settings = Settings()
    engine = StockfishEngine(settings)
    board = chess.Board()

    result = engine.analyse(board)

    assert result.best_move is None
    assert result.depth == 0
    assert result.score_cp == engine._material_score(board)


def test_resolve_command_prefers_existing_path() -> None:
    settings = Settings()
    with tempfile.NamedTemporaryFile() as handle:
        settings.stockfish_path = Path(handle.name)
        engine = StockfishEngine(settings)
        resolved = engine._resolve_command()

    assert resolved == str(settings.stockfish_path)


def test_resolve_command_uses_shutil_which() -> None:
    settings = Settings()
    settings.stockfish_path = Path("missing-stockfish")
    engine = StockfishEngine(settings)

    with (
        patch("tactix.stockfish_runner.Path.exists", return_value=False),
        patch("tactix.stockfish_runner.shutil.which", return_value="/usr/bin/stockfish"),
    ):
        resolved = engine._resolve_command()

    assert resolved == "/usr/bin/stockfish"
    assert settings.stockfish_path == Path("/usr/bin/stockfish")


def test_build_limit_prefers_depth() -> None:
    settings = Settings()
    engine = StockfishEngine(settings)

    settings.stockfish_depth = 12
    depth_limit = engine._build_limit()
    assert depth_limit.depth == 12

    settings.stockfish_depth = None
    settings.stockfish_movetime_ms = 250
    time_limit = engine._build_limit()
    assert time_limit.time == 0.25


def test_restart_handles_engine_quit_errors() -> None:
    settings = Settings()
    engine = StockfishEngine(settings)
    engine.engine = MagicMock()
    engine.engine.quit.side_effect = chess.engine.EngineError("boom")

    with patch.object(engine, "_start_engine") as start:
        engine.restart()

    start.assert_called_once()


def test_resolve_command_returns_none_when_missing() -> None:
    settings = Settings()
    settings.stockfish_path = Path("missing-stockfish")
    engine = StockfishEngine(settings)

    with (
        patch("tactix.stockfish_runner.Path.exists", return_value=False),
        patch("tactix.stockfish_runner.shutil.which", return_value=None),
    ):
        assert engine._resolve_command() is None


def test_option_helpers_handle_managed_and_coerce() -> None:
    class ManagedMeta:
        managed = True

    assert StockfishEngine._is_option_managed(ManagedMeta()) is True
    assert StockfishEngine._coerce_option_value(object()) is None


def test_configure_engine_skips_invalid_options() -> None:
    settings = Settings()
    engine = StockfishEngine(settings)

    engine._configure_engine()
    assert engine.applied_options == {}

    class OptionMeta:
        def is_managed(self) -> bool:
            return False

    engine.engine = MagicMock()
    engine.engine.options = {"Foo": OptionMeta()}
    with patch.object(engine, "_build_engine_options", return_value={"Foo": object()}):
        engine._configure_engine()

    engine.engine.configure.assert_not_called()


def test_start_engine_warns_when_missing_binary() -> None:
    settings = Settings()
    engine = StockfishEngine(settings)

    with (
        patch.object(engine, "_resolve_command", return_value=None),
        patch("tactix.stockfish_runner.logger.warning") as warn,
    ):
        engine._start_engine()

    assert engine.engine is None
    warn.assert_called_once()
