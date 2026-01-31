from __future__ import annotations

from tactix.write_analysis_checkpoint__pipeline import _write_analysis_checkpoint


def _maybe_write_analysis_checkpoint(
    analysis_checkpoint_path,
    analysis_signature: str,
    index: int,
) -> None:
    if analysis_checkpoint_path is None:
        return
    _write_analysis_checkpoint(analysis_checkpoint_path, analysis_signature, index)
