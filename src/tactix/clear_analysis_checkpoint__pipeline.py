from __future__ import annotations


def _clear_analysis_checkpoint(checkpoint_path) -> None:
    if checkpoint_path.exists():
        checkpoint_path.unlink()
