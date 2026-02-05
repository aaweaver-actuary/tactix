"""Direct execution coverage for small modules."""

from __future__ import annotations

from pathlib import Path
from queue import Queue
import runpy
import sys
import types

from fastapi.responses import StreamingResponse


def test_direct_file_execution() -> None:
    root = Path(__file__).resolve().parents[1]
    to_int_module = runpy.run_path(str(root / "src/tactix/utils/to_int.py"))
    to_int = to_int_module["to_int"]
    assert to_int("8") == 8
    assert to_int("nope") is None

    job_stream_path = root / "src/tactix/job_stream.py"
    job_stream_module = types.ModuleType("job_stream_exec")
    job_stream_module.__file__ = str(job_stream_path)
    sys.modules[job_stream_module.__name__] = job_stream_module
    job_stream_namespace: dict[str, object] = job_stream_module.__dict__
    exec(compile(job_stream_path.read_text(), str(job_stream_path), "exec"), job_stream_namespace)
    job_stream_namespace["_stream_job_response"] = lambda *_args, **_kwargs: StreamingResponse(
        iter(())
    )
    job_stream_namespace["stream_jobs"]()

    queue: Queue[object] = Queue()
    job_stream_namespace["_streaming_response"](queue, object())

    runpy.run_path(str(root / "src/tactix/sync_contexts.py"))
    runpy.run_path(str(root / "src/tactix/_normalize_clock_parts.py"))

    runpy.run_path(str(root / "src/tactix/dashboard_cache_state__api_cache.py"))
