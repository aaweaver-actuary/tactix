from __future__ import annotations


def normalize_string(value: str | None) -> str:
    """
    Normalizes a string by stripping leading and trailing whitespace and converting to lowercase.

    Parameters
    ----------
    value : str or None
        The input string to normalize. If None, an empty string is used.

    Returns
    -------
    str
        The normalized string, with whitespace removed from both ends and all characters
        converted to lowercase.

    Raises
    ------
    None

    Examples
    --------
    >>> normalize_string("  Hello World  ")
    'hello world'
    >>> normalize_string(None)
    ''
    >>> normalize_string("  PYTHON  ")
    'python'

    Commentary
    ----------
    This function provides a simple utility for normalizing strings, which is a common
    requirement in data cleaning and preprocessing tasks. While useful, its functionality is
    quite basic and generic. In a large project, it may make more sense to group this function
    with other string normalization or utility functions in a single module, rather than
    having it as a standalone module. This would help maintain logical cohesion and reduce
    fragmentation of utility code.
    """
    return (value or "").strip().lower()
