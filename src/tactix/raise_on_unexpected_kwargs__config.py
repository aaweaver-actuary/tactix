from __future__ import annotations


def _raise_on_unexpected_kwargs(kwargs: dict[str, object]) -> None:
    if kwargs:
        unexpected = next(iter(kwargs))
        raise TypeError(f"Settings.__init__() got an unexpected keyword argument '{unexpected}'")
