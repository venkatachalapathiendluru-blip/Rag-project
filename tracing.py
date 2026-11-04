"""Dependency-free request tracing for the RAG pipeline.

Each request becomes one JSON line holding its stages, latencies, token usage,
retrieved chunk IDs and guardrail decisions. Questions and answers are stored
with sensitive values masked, and tracing failures never break a request.
"""

from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
from functools import wraps
import json
import os
from pathlib import Path
import time
import uuid

from guardrails import redact_pii


TRACE_DIR = Path(
    os.getenv("RAG_TRACE_DIR", Path(__file__).resolve().parent / "traces")
)

_current_trace = ContextVar("current_rag_trace", default=None)


def _masked(text):
    return redact_pii(text or "")[0]


@contextmanager
def trace_request(question):
    """Open a trace for one request and write it out when the request ends."""

    trace = {
        "trace_id": uuid.uuid4().hex,
        "started_at": datetime.now(timezone.utc).isoformat(),
        "question": _masked(question),
        "status": "ok",
        "spans": [],
        "attributes": {},
        "tokens": {"prompt": 0, "completion": 0, "total": 0},
    }
    token = _current_trace.set(trace)
    started = time.perf_counter()

    try:
        yield trace
    except Exception as error:
        trace["status"] = "error"
        trace["error_type"] = type(error).__name__
        raise
    finally:
        trace["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
        _current_trace.reset(token)
        _write_trace(trace)


@contextmanager
def span(name):
    """Time one pipeline stage inside the current trace."""

    trace = _current_trace.get()
    started = time.perf_counter()
    record = {"name": name, "status": "ok"}

    try:
        yield record
    except Exception as error:
        record["status"] = "error"
        record["error_type"] = type(error).__name__
        raise
    finally:
        record["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)

        if trace is not None:
            trace["spans"].append(record)


def traced(name):
    """Decorator form of span()."""

    def decorator(function):
        @wraps(function)
        def wrapper(*args, **kwargs):
            with span(name):
                return function(*args, **kwargs)

        return wrapper

    return decorator


def annotate(**attributes):
    """Attach values such as chunk IDs or guardrail decisions to the trace."""

    trace = _current_trace.get()

    if trace is not None:
        trace["attributes"].update(attributes)


def set_status(status):
    trace = _current_trace.get()

    if trace is not None:
        trace["status"] = status


def set_answer(answer):
    trace = _current_trace.get()

    if trace is not None:
        trace["answer"] = _masked(answer)


def record_usage(response):
    """Add the token usage of an OpenAI-compatible response to the trace."""

    trace = _current_trace.get()
    usage = getattr(response, "usage", None)

    if trace is None or usage is None:
        return

    for key, attribute in (
        ("prompt", "prompt_tokens"),
        ("completion", "completion_tokens"),
        ("total", "total_tokens"),
    ):
        value = getattr(usage, attribute, 0)

        if isinstance(value, int):
            trace["tokens"][key] += value


def _write_trace(trace):
    try:
        TRACE_DIR.mkdir(parents=True, exist_ok=True)
        day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        with open(TRACE_DIR / f"traces-{day}.jsonl", "a", encoding="utf-8") as file:
            file.write(json.dumps(trace, ensure_ascii=False, default=str) + "\n")
    except OSError as error:
        print(f"Trace could not be written: {type(error).__name__}")
