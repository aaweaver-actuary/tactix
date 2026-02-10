"""Compute tactic severity scores."""

from dataclasses import dataclass
from typing import cast

from tactix._apply_fork_severity_floor import _apply_fork_severity_floor
from tactix._severity_for_result import _severity_for_result
from tactix.analyze_tactics__positions import _SEVERITY_MAX, _SEVERITY_MIN
from tactix.config import Settings
from tactix.legacy_args import apply_legacy_args, apply_legacy_kwargs, init_legacy_values
from tactix.utils.logger import funclogger

_SEVERITY_KEYS = ("base_cp", "delta", "motif", "mate_in", "result", "settings")


@dataclass(frozen=True)
class SeverityContext:
    base_cp: int
    delta: int
    motif: str
    mate_in: int | None
    result: str
    settings: Settings | None


@dataclass(frozen=True)
class SeverityInputs:
    """Explicit inputs for building severity contexts."""

    base_cp: int
    delta: int
    motif: str
    mate_in: int | None
    result: str
    settings: Settings | None


@funclogger
def _init_severity_values(params: SeverityContext | None) -> dict[str, object]:
    values = init_legacy_values(_SEVERITY_KEYS)
    if params is None:
        return values
    values.update(
        {
            "base_cp": params.base_cp,
            "delta": params.delta,
            "motif": params.motif,
            "mate_in": params.mate_in,
            "result": params.result,
            "settings": params.settings,
        }
    )
    return values


@funclogger
def _apply_severity_base_cp(values: dict[str, object], context: int | None) -> None:
    if context is None:
        return
    if values["base_cp"] is not None:
        raise TypeError("base_cp provided multiple times")
    values["base_cp"] = context


@funclogger
def build_severity_context(inputs: SeverityInputs) -> SeverityContext:
    """Build a severity context from explicit inputs."""
    return SeverityContext(
        base_cp=inputs.base_cp,
        delta=inputs.delta,
        motif=inputs.motif,
        mate_in=inputs.mate_in,
        result=inputs.result,
        settings=inputs.settings,
    )


@funclogger
def _build_severity_context(values: dict[str, object]) -> SeverityContext:
    if values["base_cp"] is None:
        raise TypeError("base_cp, delta, motif, and result are required")
    if values["delta"] is None or values["motif"] is None or values["result"] is None:
        raise TypeError("base_cp, delta, motif, and result are required")
    base_cp = cast(int, values["base_cp"])
    delta = cast(int, values["delta"])
    motif = cast(str, values["motif"])
    mate_in = cast(int | None, values["mate_in"])
    result = cast(str, values["result"])
    settings = cast(Settings | None, values["settings"])
    inputs = SeverityInputs(
        **dict(
            zip(
                _SEVERITY_KEYS,
                (base_cp, delta, motif, mate_in, result, settings),
                strict=True,
            )
        )
    )
    return build_severity_context(inputs)


@funclogger
def _resolve_severity_context(
    context: SeverityContext | int | None,
    args: tuple[object, ...],
    params: SeverityContext | None,
    legacy: dict[str, object],
) -> SeverityContext:
    if isinstance(context, SeverityContext):
        return context
    values = _init_severity_values(params)
    _apply_severity_base_cp(values, context)
    apply_legacy_kwargs(values, _SEVERITY_KEYS, legacy)
    apply_legacy_args(values, _SEVERITY_KEYS[1:], args)
    return _build_severity_context(values)


@funclogger
def _compute_severity__tactic(
    *args: object,
    params: SeverityContext | None = None,
    **legacy: object,
) -> float:
    context = None
    remaining_args = args
    if args:
        context = cast(SeverityContext | int | None, args[0])
        remaining_args = args[1:]
    if "context" in legacy and context is None:
        context = cast(SeverityContext | int | None, legacy.pop("context"))
    resolved = _resolve_severity_context(context, remaining_args, params, legacy)
    severity = _severity_for_result(
        resolved.base_cp,
        resolved.delta,
        resolved.motif,
        resolved.mate_in,
        resolved.result,
    )
    if resolved.motif == "hanging_piece":
        severity = max(severity, _SEVERITY_MIN)
    severity = min(severity, _SEVERITY_MAX)
    return _apply_fork_severity_floor(severity, resolved.motif, resolved.settings)
