import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock

import tracing
from trace_report import load_traces, percentile, summarize


class TracingTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = Path(directory.name)
        patcher = mock.patch.object(tracing, "TRACE_DIR", self.directory)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _lines(self):
        return [
            json.loads(line)
            for path in self.directory.glob("*.jsonl")
            for line in path.read_text(encoding="utf-8").splitlines()
        ]

    def test_trace_records_stages_tokens_and_masks_pii(self):
        usage = SimpleNamespace(prompt_tokens=10, completion_tokens=5, total_tokens=15)

        with tracing.trace_request("Mail a.person@example.com"):
            with tracing.span("generate"):
                tracing.record_usage(SimpleNamespace(usage=usage))
            tracing.annotate(retrieved_chunk_ids=[1, 2])
            tracing.set_answer("Call +91 98765 43210")

        trace = self._lines()[0]
        self.assertEqual(trace["status"], "ok")
        self.assertEqual(trace["spans"][0]["name"], "generate")
        self.assertEqual(trace["tokens"]["total"], 15)
        self.assertEqual(trace["attributes"]["retrieved_chunk_ids"], [1, 2])
        self.assertNotIn("example.com", json.dumps(trace))
        self.assertNotIn("98765", json.dumps(trace))

    def test_errors_are_recorded_and_still_raised(self):
        with self.assertRaises(ValueError):
            with tracing.trace_request("question"):
                with tracing.span("generate"):
                    raise ValueError("secret detail")

        trace = self._lines()[0]
        self.assertEqual(trace["status"], "error")
        self.assertEqual(trace["error_type"], "ValueError")
        self.assertEqual(trace["spans"][0]["status"], "error")
        self.assertNotIn("secret detail", json.dumps(trace))

    def test_helpers_are_safe_without_an_active_trace(self):
        tracing.annotate(a=1)
        tracing.set_status("blocked")
        tracing.record_usage(SimpleNamespace(usage=None))

        with tracing.span("alone"):
            pass

        self.assertEqual(self._lines(), [])

    def test_report_summarizes_requests(self):
        with tracing.trace_request("one"):
            tracing.annotate(
                input_guardrail_reasons=["role_hijack"],
                citations_valid=False,
                flagged_chunk_ids=[4],
            )
            tracing.set_status("blocked")

        summary = summarize(load_traces(self.directory))
        self.assertEqual(summary["requests"], 1)
        self.assertEqual(summary["statuses"], {"blocked": 1})
        self.assertEqual(summary["guardrail_events"], {"role_hijack": 1})
        self.assertEqual(summary["citation_failures"], 1)
        self.assertEqual(summary["chunks_with_injection_removed"], 1)

    def test_percentile_uses_nearest_rank(self):
        self.assertEqual(percentile([1, 2, 3, 4], 50), 2)
        self.assertEqual(percentile([1, 2, 3, 4], 95), 4)
        self.assertIsNone(percentile([], 50))


if __name__ == "__main__":
    unittest.main()
