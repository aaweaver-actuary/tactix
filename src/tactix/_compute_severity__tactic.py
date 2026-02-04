from dataclasses import dataclass
from typing import cast

from tactix._apply_fork_severity_floor import _apply_fork_severity_floor
from tactix._severity_for_result import _severity_for_result
from tactix.analyze_tactics__positions import _SEVERITY_MAX
from tactix.config import Settings
from tactix.utils.logger import funclogger


@dataclass(frozen=True)
class SeverityContext:
    base_cp: int
    delta: int
    motif: str
    mate_in: int | None
    result: str
    settings: Settings | None


def _init_severity_values(params: SeverityContext | None) -> dict[str, object]:
    values: dict[str, object] = {
        "base_cp": None,
        "delta": None,
        "motif": None,
        "mate_in": None,
        "result": None,
        "settings": None,
    }
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


def _apply_severity_base_cp(values: dict[str, object], context: int | None) -> None:
    if context is None:
        return
    if values["base_cp"] is not None:
        raise TypeError("base_cp provided multiple times")
    values["base_cp"] = context


def _apply_severity_legacy(values: dict[str, object], legacy: dict[str, object]) -> None:
    for key in tuple(values.keys()):
        if key in legacy:
            values[key] = legacy.pop(key)
    if legacy:
        raise TypeError(f"Unexpected keyword arguments: {', '.join(sorted(legacy))}")


def _apply_severity_args(values: dict[str, object], args: tuple[object, ...]) -> None:
    if not args:
        return
    ordered_keys = ("delta", "motif", "mate_in", "result", "settings")
    if len(args) > len(ordered_keys):
        raise TypeError("Too many positional arguments")
    for key, value in zip(ordered_keys, args, strict=False):
        if values[key] is not None:
            raise TypeError(f"{key} provided multiple times")
        values[key] = value


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
    return SeverityContext(
        base_cp=base_cp,
        delta=delta,
        motif=motif,
        mate_in=mate_in,
        result=result,
        settings=settings,
    )


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
    _apply_severity_legacy(values, legacy)
    _apply_severity_args(values, args)
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
    severity = min(severity, _SEVERITY_MAX)
    return _apply_fork_severity_floor(severity, resolved.motif, resolved.settings)
