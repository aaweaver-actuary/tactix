"""Compatibility re-exports for the mock database store."""

from __future__ import annotations

from tactix import define_mock_store__db as _impl

__all__ = [name for name in dir(_impl) if not name.startswith("__")]
globals().update({name: getattr(_impl, name) for name in __all__})
