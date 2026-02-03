from __future__ import annotations

import time

from tactix.pipeline_state__pipeline import ProgressCallback


def _emit_progress(progress: ProgressCallback | None, step: str, **fields: object) -> None:
    """
    Emits a progress update by invoking the provided callback with a payload
    containing the current step, timestamp, and any additional fields.

    Parameters
    ----------
    progress : callable or None
        A callback function that accepts a single dictionary
        argument representing the progress payload.
        If None, no action is taken.
    step : str
        A string indicating the current step or stage of the process.
    **fields : object
        Additional keyword arguments to include in the progress payload.
        Each key-value pair is added to the payload dictionary.

    Returns
    -------
    None

    Raises
    ------
    None

    Examples
    --------
    >>> def my_progress_callback(payload):
    ...     print(payload)
    ...
    >>> _emit_progress(my_progress_callback, "loading_data", percent=50)
    {'step': 'loading_data', 'timestamp': 1700000000.0, 'percent': 50}

    >>> _emit_progress(None, "processing")  # No output, as progress is None
    """
    if progress is None:
        return
    payload: dict[str, object] = {"step": step, "timestamp": time.time()}
    payload.update(fields)
    progress(payload)
