import hashlib
from pathlib import Path

import pytest

from tactix.stockfish_runner import verify_stockfish_checksum


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
