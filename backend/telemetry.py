"""Request logging and summaries of the traces the pipeline writes."""

import json
import logging
import sys
import time
import uuid

from fastapi import Request

from trace_report import load_traces, summarize


class JsonFormatter(logging.Formatter):
    FIELDS = ("request_id", "method", "path", "status", "duration_ms", "error_type", "job_id")

    def format(self, record):
        entry = {"level": record.levelname, "logger": record.name, "event": record.getMessage()}

        for field in self.FIELDS:
            value = getattr(record, field, None)

            if value is not None:
                entry[field] = value

        return json.dumps(entry)


def configure_logging():
    root = logging.getLogger("rag")

    if not root.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JsonFormatter())
        root.addHandler(handler)
        root.setLevel(logging.INFO)
        root.propagate = False


access = logging.getLogger("rag.access")


async def request_context(request: Request, call_next):
    """Give each request an ID and log it. Bodies and headers are never logged."""

    supplied = request.headers.get("x-request-id", "")
    request_id = supplied if supplied.isalnum() and len(supplied) <= 64 else uuid.uuid4().hex
    request.state.request_id = request_id
    started = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    access.info(
        "request",
        extra={
            "request_id": request_id,
            "method": request.method,
            "path": request.url.path,
            "status": response.status_code,
            "duration_ms": round((time.perf_counter() - started) * 1000, 1),
        },
    )
    return response


def metrics_summary(trace_directory, recent=25):
    traces = load_traces(trace_directory)
    summary = summarize(traces)
    newest = sorted(traces, key=lambda item: item.get("started_at", ""), reverse=True)
    summary["recent_errors"] = [
        {
            "trace_id": item.get("trace_id"),
            "started_at": item.get("started_at"),
            "error_type": item.get("error_type"),
        }
        for item in newest
        if item.get("status") == "error"
    ][:recent]
    summary["recent_requests"] = [
        {
            "trace_id": item.get("trace_id"),
            "started_at": item.get("started_at"),
            "status": item.get("status"),
            "duration_ms": item.get("duration_ms"),
            "total_tokens": item.get("tokens", {}).get("total"),
        }
        for item in newest[:recent]
    ]
    return summary
