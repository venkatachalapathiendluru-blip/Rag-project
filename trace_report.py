"""Summarize request traces: traffic, failures, latency and token usage.

Usage: python trace_report.py [trace_directory]
"""

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

from tracing import TRACE_DIR


def percentile(values, percent):
    """Nearest-rank percentile, or None when there are no values."""

    if not values:
        return None

    ordered = sorted(values)
    rank = max(1, -(-len(ordered) * percent // 100))
    return ordered[int(rank) - 1]


def load_traces(directory):
    traces = []

    for path in sorted(Path(directory).glob("traces-*.jsonl")):
        with open(path, encoding="utf-8") as file:
            for line in file:
                try:
                    traces.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    return traces


def summarize(traces):
    stage_latency = defaultdict(list)
    block_reasons = Counter()
    statuses = Counter()
    citation_failures = 0
    flagged_chunks = 0

    for trace in traces:
        statuses[trace.get("status", "unknown")] += 1
        attributes = trace.get("attributes", {})
        block_reasons.update(attributes.get("input_guardrail_reasons", []))
        block_reasons.update(attributes.get("output_guardrail_reasons", []))
        citation_failures += attributes.get("citations_valid") is False
        flagged_chunks += len(attributes.get("flagged_chunk_ids", []))

        for item in trace.get("spans", []):
            stage_latency[item["name"]].append(item["duration_ms"])

    return {
        "requests": len(traces),
        "statuses": dict(statuses),
        "guardrail_events": dict(block_reasons),
        "citation_failures": citation_failures,
        "chunks_with_injection_removed": flagged_chunks,
        "total_tokens": sum(t.get("tokens", {}).get("total", 0) for t in traces),
        "latency_ms": {
            "request": {
                "p50": percentile([t.get("duration_ms", 0) for t in traces], 50),
                "p95": percentile([t.get("duration_ms", 0) for t in traces], 95),
            },
            **{
                name: {
                    "p50": percentile(values, 50),
                    "p95": percentile(values, 95),
                }
                for name, values in stage_latency.items()
            },
        },
    }


if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else TRACE_DIR
    print(json.dumps(summarize(load_traces(directory)), indent=2))
