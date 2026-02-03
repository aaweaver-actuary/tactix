import hashlib


class Hasher:
    """
    Hasher provides static methods for generating SHA256 hashes from strings, bytes, and files.

    Methods
    -------
    hash_string(input_string: str) -> str
        Returns a SHA256 hash of the input string.
    hash_bytes(input_bytes: bytes) -> str
        Returns a SHA256 hash of the input bytes.
    hash_file(file_path: str) -> str
        Returns a SHA256 hash of the contents of the specified file.
    """

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
    """
    Hashes the given data using the Hasher utility.

    Depending on the type of input and the `is_bytes` flag, this function delegates
    to either `Hasher.hash_bytes` or `Hasher.hash_string` to compute a hash of the
    input data.

    Parameters
    ----------
    data : str or bytes
        The data to be hashed. If `is_bytes` is True, this should be a bytes object;
        otherwise, it should be a string.
    is_bytes : bool, optional
        If True, treats `data` as bytes and uses `Hasher.hash_bytes`. If False,
        treats `data` as a string and uses `Hasher.hash_string`. Default is False.

    Returns
    -------
    str
        The hexadecimal string representation of the hash of the input data.

    Raises
    ------
    TypeError
        If `is_bytes` is True and `data` is not of type bytes, or if `is_bytes` is
        False and `data` is not of type str.

    Examples
    --------
    >>> hash("hello world")
    '5eb63bbbe01eeed093cb22bb8f5acdc3'

    >>> hash(b"hello world", is_bytes=True)
    '5eb63bbbe01eeed093cb22bb8f5acdc3'

    Commentary
    ----------
    As a standalone function, `hash` serves as a thin wrapper around the `Hasher`
    class, providing a unified interface for hashing both strings and bytes. While
    this can be convenient, in a large project it may be preferable to integrate
    this functionality directly into a broader utility module or class that handles
    all hashing and encoding concerns, rather than maintaining a single-purpose
    module for such a simple wrapper. This would help group related functionality
    and reduce fragmentation of utility code.
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
