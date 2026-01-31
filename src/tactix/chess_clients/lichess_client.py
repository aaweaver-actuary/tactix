from __future__ import annotations

from importlib import import_module

_legacy = import_module("tactix.lichess_client")

__all__ = list(getattr(_legacy, "__all__", []))


def __getattr__(name: str):
    return getattr(_legacy, name)


def __dir__() -> list[str]:
    return sorted(set(list(globals().keys()) + __all__))


_VULTURE_WHITELIST = (__getattr__, __dir__)
