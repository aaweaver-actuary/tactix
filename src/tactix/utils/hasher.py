import hashlib


class Hasher:
    """Utility class for hashing data."""

    @staticmethod
    def hash_string(input_string: str) -> str:
        """Returns a SHA256 hash of the input string."""

        return hashlib.sha256(input_string.encode("utf-8")).hexdigest()

    @staticmethod
    def hash_bytes(input_bytes: bytes) -> str:
        """Returns a SHA256 hash of the input bytes."""

        return hashlib.sha256(input_bytes).hexdigest()

    @staticmethod
    def hash_file(file_path: str) -> str:
        """Returns a SHA256 hash of the contents of the specified file."""

        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256.update(chunk)
        return sha256.hexdigest()


def hash(data: str | bytes, is_bytes: bool = False) -> str:
    """Hash data using SHA-256.

    Args:
        data: The input data to hash, either as a string or bytes.
        is_bytes: Whether the input data is in bytes. Defaults to False.

    Returns:
        The SHA-256 hash of the input data as a hexadecimal string.
    """
    if is_bytes:
        return Hasher.hash_bytes(data)  # type: ignore
    return Hasher.hash_string(data)  # type: ignore


def hash_file(file_path: str) -> str:
    """Hash the contents of a file using SHA-256.

    Args:
        file_path: The path to the file to hash.

    Returns:
        The SHA-256 hash of the file contents as a hexadecimal string.
    """
    return Hasher.hash_file(file_path)
