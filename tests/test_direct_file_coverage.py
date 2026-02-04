"""Direct execution coverage for small modules."""

from __future__ import annotations

from pathlib import Path
from queue import Queue
import runpy

from fastapi.responses import StreamingResponse


def test_direct_file_execution() -> None:
    root = Path(__file__).resolve().parents[1]
    to_int_module = runpy.run_path(str(root / "src/tactix/utils/to_int.py"))
    to_int = to_int_module["to_int"]
    assert to_int("8") == 8
    assert to_int("nope") is None

    stream_jobs_path = root / "src/tactix/stream_jobs__api.py"
    stream_jobs_namespace: dict[str, object] = {
        "__file__": str(stream_jobs_path),
        "__name__": "stream_jobs__api_exec",
    }
    exec(
        compile(stream_jobs_path.read_text(), str(stream_jobs_path), "exec"), stream_jobs_namespace
    )
    stream_jobs_namespace["_stream_job_response"] = lambda *_args, **_kwargs: StreamingResponse(
        iter(())
    )
    stream_jobs_namespace["stream_jobs"]()

    streaming_response_path = root / "src/tactix/streaming_response__job_stream.py"
    streaming_response_namespace: dict[str, object] = {
        "__file__": str(streaming_response_path),
        "__name__": "streaming_response__job_stream_exec",
    }
    exec(
        compile(streaming_response_path.read_text(), str(streaming_response_path), "exec"),
        streaming_response_namespace,
    )
    queue: Queue[object] = Queue()
    streaming_response_namespace["_streaming_response"](queue, object())

    runpy.run_path(str(root / "src/tactix/DailySyncStartContext.py"))
    runpy.run_path(str(root / "src/tactix/FetchProgressContext_1.py"))

    runpy.run_path(str(root / "src/tactix/dashboard_cache_state__api_cache.py"))
