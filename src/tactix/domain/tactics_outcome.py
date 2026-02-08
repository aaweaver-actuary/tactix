"""Domain rules for tactic outcome evaluation."""

from __future__ import annotations

from typing import Any

from tactix.outcome_context import BaseOutcomeContext
from tactix.unclear_outcome_params import UnclearOutcomeParams


def should_override_failed_attempt(
    result: str,
    swing: int | None,
    threshold: int | None,
    target_motif: str,
) -> bool:
    """Return True when a failed attempt override should apply."""
    return bool(
        result == "unclear"
        and swing is not None
        and threshold is not None
        and swing < threshold
        and target_motif
    )


def resolve_unclear_outcome_context(
    context: BaseOutcomeContext | str,
    threshold: int | str | None,
    args: tuple[Any, ...],
    params: UnclearOutcomeParams | None,
    legacy: dict[str, Any],
) -> tuple[BaseOutcomeContext, int | None]:
    values = _init_unclear_values(params)
    _apply_unclear_legacy(values, legacy)
    _apply_unclear_args(values, args)
    _apply_unclear_threshold(values, threshold)
    _coerce_unclear_threshold(context, values)
    resolved = _build_unclear_context(context, values)
    return resolved, values["threshold"]


def _unclear_value_keys() -> tuple[str, ...]:
    return ("motif", "best_move", "user_move_uci", "swing", "threshold")


def _init_unclear_values(
    params: UnclearOutcomeParams | None,
) -> dict[str, Any]:
    values: dict[str, Any] = dict.fromkeys(_unclear_value_keys())
    if params is None:
        return values
    values.update(
        {
            "motif": params.motif,
            "best_move": params.best_move,
            "user_move_uci": params.user_move_uci,
            "swing": params.swing,
            "threshold": params.threshold,
        }
    )
    return values


def _apply_unclear_legacy(values: dict[str, Any], legacy: dict[str, Any]) -> None:
    for key in tuple(values.keys()):
        if key in legacy:
            values[key] = legacy.pop(key)
    if legacy:
        raise TypeError(f"Unexpected keyword arguments: {', '.join(sorted(legacy))}")


def _apply_unclear_args(values: dict[str, Any], args: tuple[Any, ...]) -> None:
    if not args:
        return
    ordered_keys = _unclear_value_keys()
    if len(args) > len(ordered_keys):
        raise TypeError("Too many positional arguments")
    for key, value in zip(ordered_keys, args, strict=False):
        if values[key] is not None:
            raise TypeError(f"{key} provided multiple times")
        values[key] = value


def _apply_int_threshold(values: dict[str, Any], threshold: int) -> None:
    current = values["threshold"]
    if current is None:
        values["threshold"] = threshold
        return
    if current != threshold:
        raise TypeError("threshold provided multiple times")


def _apply_str_threshold(values: dict[str, Any], threshold: str) -> None:
    if values["motif"] is None:
        values["motif"] = threshold
        return
    raise TypeError("threshold provided multiple times")


def _apply_unclear_threshold(values: dict[str, Any], threshold: int | str | None) -> None:
    if threshold is None:
        return
    if isinstance(threshold, int):
        _apply_int_threshold(values, threshold)
        return
    if isinstance(threshold, str):
        _apply_str_threshold(values, threshold)
        return
    raise TypeError("threshold provided multiple times")


def _should_coerce_unclear_threshold(
    context: BaseOutcomeContext | str,
    values: dict[str, Any],
) -> bool:
    return all(
        (
            isinstance(context, BaseOutcomeContext),
            values["threshold"] is None,
            values["user_move_uci"] is None,
            values["best_move"] is None,
            values["swing"] is None,
            isinstance(values["motif"], int),
        )
    )


def _coerce_unclear_threshold(
    context: BaseOutcomeContext | str,
    values: dict[str, Any],
) -> None:
    if not _should_coerce_unclear_threshold(context, values):
        return
    values["threshold"] = values["motif"]
    values["motif"] = None


def _build_unclear_context(
    context: BaseOutcomeContext | str,
    values: dict[str, Any],
) -> BaseOutcomeContext:
    if isinstance(context, BaseOutcomeContext):
        return context
    if values["motif"] is None or values["user_move_uci"] is None:
        raise TypeError("result, motif, and user_move_uci are required")
    return BaseOutcomeContext(
        result=context,
        motif=values["motif"],
        best_move=values["best_move"],
        user_move_uci=values["user_move_uci"],
        swing=values["swing"],
    )
