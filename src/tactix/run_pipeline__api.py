"""API endpoint to run the pipeline with explicit date ranges."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, HTTPException

from tactix.app.use_cases.pipeline_run import (
    PipelineRunUseCase,
    PipelineWindowError,
    get_pipeline_run_use_case,
)
from tactix.pipeline_run_filters import PipelineRunFilters


def run_pipeline(  # pragma: no cover
    filters: Annotated[PipelineRunFilters, Depends()],
    use_case: Annotated[PipelineRunUseCase, Depends(get_pipeline_run_use_case)],
) -> dict[str, object]:
    """Run the pipeline for the provided date range and return counts."""
    try:
        return use_case.run(filters)
    except PipelineWindowError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


__all__ = ["run_pipeline"]
