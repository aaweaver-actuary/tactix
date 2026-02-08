"""Unit of work port abstraction."""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, TypeVar

ConnT_co = TypeVar("ConnT_co", covariant=True)


class UnitOfWork(Protocol[ConnT_co]):
    """Define the session boundary for database operations."""

    def begin(self) -> ConnT_co | None:
        """Start a unit of work and return the active connection."""

    def commit(self) -> None:
        """Commit the active unit of work."""

    def rollback(self) -> None:
        """Rollback the active unit of work."""

    def close(self) -> None:
        """Release the underlying connection resources."""


UnitOfWorkFactory = Callable[..., UnitOfWork[ConnT_co]]
