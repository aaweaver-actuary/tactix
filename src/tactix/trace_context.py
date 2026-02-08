"""Context helpers for run-level traceability."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_RUN_ID: ContextVar[str | None] = ContextVar("tactix_run_id", default=None)
_OP_ID: ContextVar[str | None] = ContextVar("tactix_op_id", default=None)


def get_run_id() -> str | None:
    """Return the active run id for the current context."""
    return _RUN_ID.get()


def get_op_id() -> str | None:
    """Return the active operation id for the current context."""
    return _OP_ID.get()


def set_run_id(value: str | None) -> ContextVar[str | None].Token:
    """Bind a run id to the current context."""
    return _RUN_ID.set(value)


def reset_run_id(token: ContextVar[str | None].Token) -> None:
    """Reset the run id context to a previous value."""
    _RUN_ID.reset(token)


def set_op_id(value: str | None) -> ContextVar[str | None].Token:
    """Bind an operation id to the current context."""
    return _OP_ID.set(value)


def reset_op_id(token: ContextVar[str | None].Token) -> None:
    """Reset the operation id context to a previous value."""
    _OP_ID.reset(token)


@contextmanager
def trace_context(
    *,
    run_id: str | None = None,
    op_id: str | None = None,
) -> Iterator[None]:
    """Temporarily bind run/op identifiers to the current context."""
    run_token = set_run_id(run_id) if run_id is not None else None
    op_token = set_op_id(op_id) if op_id is not None else None
    try:
        yield
    finally:
        if op_token is not None:
            reset_op_id(op_token)
        if run_token is not None:
            reset_run_id(run_token)


__all__ = [
    "get_op_id",
    "get_run_id",
    "reset_op_id",
    "reset_run_id",
    "set_op_id",
    "set_run_id",
    "trace_context",
]
