from __future__ import annotations

from collections.abc import Callable

from tactix.compute_pgn_hashes__pipeline import _compute_pgn_hashes
from tactix.count_hash_matches__pipeline import _count_hash_matches
from tactix.GameRow import GameRow
from tactix.raise_for_hash_mismatch__pipeline import _raise_for_hash_mismatch


def _validate_raw_pgn_hashes(
    rows: list[GameRow],
    source: str,
    fetch_latest_pgn_hashes: Callable[[list[str], str], dict[str, str]],
) -> dict[str, int]:
    """
    Validates raw PGN hashes for a set of chess games by comparing computed hashes
    with those stored in the database.

    Parameters
    ----------
    rows : list of GameRow
        List of game rows containing raw PGN data to be validated.
    source : str
        Identifier for the data source (e.g., 'chesscom', 'lichess').
    fetch_latest_pgn_hashes : Callable[[list[str], str], dict[str, str]]
        Fetcher returning latest hashes keyed by game id for the provided source.

    Returns
    -------
    dict of str to int
        Dictionary with the following keys:
        - 'computed': Number of PGN hashes computed from the input rows.
        - 'matched': Number of computed hashes that matched the stored hashes.

    Raises
    ------
    Exception
        Raises an exception if there is a mismatch between computed and stored
        hashes. The specific exception type and message depend on the implementation
        of `_raise_for_hash_mismatch`.

    Examples
    --------
    >>> rows = [GameRow(...), GameRow(...)]
    >>> result = _validate_raw_pgn_hashes(rows, "chesscom", fetch_latest_pgn_hashes)
    >>> print(result)
    {'computed': 2, 'matched': 2}

    Commentary
    ----------
    This function encapsulates a clear validation step for PGN hashes, which is a
    distinct and testable unit of work. However, as a private function (by naming
    convention), it may be better suited as part of a larger validation or pipeline
    module rather than a standalone module. If this is the only function in its
    module, consider combining it with related pipeline or validation logic to
    maintain a cohesive module structure.
    """
    if not rows:
        return {"computed": 0, "matched": 0}
    computed = _compute_pgn_hashes(rows, source)
    stored = fetch_latest_pgn_hashes(list(computed.keys()), source)
    matched = _count_hash_matches(computed, stored)
    _raise_for_hash_mismatch(source, computed, stored, matched)
    return {"computed": len(computed), "matched": matched}
