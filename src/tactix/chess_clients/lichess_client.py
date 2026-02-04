"""Lichess client shim for chess_clients namespace."""

from __future__ import annotations

from tactix import lichess_client as _client

__all__ = list(_client.__all__)

_exports = {name: getattr(_client, name) for name in __all__ if name != "LichessClient"}
globals().update(_exports)
LichessClient = _client.LichessClient
