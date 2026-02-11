import pytest

from tactix.raise_on_unexpected_kwargs__config import _raise_on_unexpected_kwargs
from tactix.split_pgn_chunks import split_pgn_chunks


def test_raise_on_unexpected_kwargs_noop_on_empty() -> None:
    _raise_on_unexpected_kwargs({})


def test_raise_on_unexpected_kwargs_raises_for_unexpected() -> None:
    with pytest.raises(TypeError, match="unexpected keyword argument 'extra'"):
        _raise_on_unexpected_kwargs({"extra": "value"})


def test_split_pgn_chunks_handles_empty_text() -> None:
    assert split_pgn_chunks("") == []


def test_split_pgn_chunks_splits_multiple_games() -> None:
    text = '[Event "Game 1"]\n1. e4 e5\n\n[Event "Game 2"]\n1. d4 d5\n'
    assert split_pgn_chunks(text) == [
        '[Event "Game 1"]\n1. e4 e5',
        '[Event "Game 2"]\n1. d4 d5',
    ]
