from __future__ import annotations

from tactix.clear_analysis_checkpoint__pipeline import _clear_analysis_checkpoint


def _maybe_clear_analysis_checkpoint(analysis_checkpoint_path) -> None:
    if analysis_checkpoint_path is not None:
        _clear_analysis_checkpoint(analysis_checkpoint_path)
