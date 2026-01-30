import hashlib

from tactix.utils.hasher import Hasher, hash_file
from tactix.utils.hasher import hash as hash_text


def test_hash_string_matches_sha256() -> None:
    payload = "tactix"
    expected = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    assert Hasher.hash_string(payload) == expected


def test_hash_bytes_matches_sha256() -> None:
    payload = b"tactix-bytes"
    expected = hashlib.sha256(payload).hexdigest()
    assert Hasher.hash_bytes(payload) == expected


def test_hash_file_matches_sha256(tmp_path) -> None:
    payload = b"tactix-file"
    path = tmp_path / "payload.bin"
    path.write_bytes(payload)
    expected = hashlib.sha256(payload).hexdigest()
    assert Hasher.hash_file(str(path)) == expected
    assert hash_file(str(path)) == expected


def test_hash_dispatches_by_type() -> None:
    text_payload = "dispatch"
    bytes_payload = b"dispatch-bytes"
    assert hash_text(text_payload) == Hasher.hash_string(text_payload)
    assert hash_text(bytes_payload, is_bytes=True) == Hasher.hash_bytes(bytes_payload)
