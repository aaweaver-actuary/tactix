from __future__ import annotations


def normalize_string(value: str | None) -> str:
    """
    Normalizes a string value by stripping leading and trailing whitespace and
    converting it to lowercase.

    Args:
        value (str | None): The input string to normalize. If None, it is
        treated as an empty string.

    Returns:
        str: The normalized string, or an empty string if the input is None or empty.
    """
    return (value or "").strip().lower()
