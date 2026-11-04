"""Offline tests. They need no database, network or model."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

import numpy as np
import requests

for name, value in {
    "NVIDIA_API_KEY": "test", "NVIDIA_BASE_URL": "http://localhost/none",
    "NVIDIA_MODEL": "m", "NVIDIA_RERANK_URL": "http://localhost/none",
    "NVIDIA_RERANK_MODEL": "r", "DB_PASSWORD": "test",
}.items():
    os.environ.setdefault(name, value)

import openai

from backend import chat_service, config, ingestion, reports, settings_repo
from backend.errors import ApiError
from backend.security import RateLimiter, require_token
from chunking import chunk_text
import rag_chat as engine


def response(status=200, body=None, text=None):
    item = requests.Response()
    item.status_code = status
    item._content = text.encode() if text is not None else json.dumps(body or {}).encode()
    return item


class RerankReliabilityTests(unittest.TestCase):
    rows = [(1, "a", 0.5), (2, "b", 0.4)]

    def setUp(self):
        patcher = mock.patch.object(engine.time, "sleep")
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, *results):
        return mock.patch.object(engine.requests, "post", side_effect=list(results))

    def test_sorts_by_logit_and_maps_indexes(self):
        ok = response(body={"rankings": [{"index": 0, "logit": -1}, {"index": 1, "logit": 2}]})
        with self.post(ok):
            ranked = engine.rerank_context("q", self.rows)
        self.assertEqual([row["id"] for row in ranked], [2, 1])

    def test_retries_transient_status_then_succeeds(self):
        ok = response(body={"rankings": [{"index": 0, "logit": 1}]})
        with self.post(response(503), response(429), ok) as post:
            engine.rerank_context("q", self.rows)
        self.assertEqual(post.call_count, 3)
        self.assertEqual(self.sleep.call_count, 2)

    def test_retries_timeout_and_gives_up(self):
        with self.post(*[requests.Timeout()] * 3) as post, self.assertRaises(requests.Timeout):
            engine.rerank_context("q", self.rows)
        self.assertEqual(post.call_count, 3)

    def test_does_not_retry_client_errors(self):
        with self.post(response(401)) as post, self.assertRaises(requests.HTTPError):
            engine.rerank_context("q", self.rows)
        self.assertEqual(post.call_count, 1)

    def test_rejects_malformed_responses(self):
        for bad in (
            response(text="not json"),
            response(body={"rankings": []}),
            response(body={"rankings": [{"index": 0}]}),
            response(body={"rankings": [{"index": "x", "logit": 1}]}),
            response(body={"rankings": [{"index": 99, "logit": 1}]}),
        ):
            with self.post(bad), self.assertRaises(ValueError):
                engine.rerank_context("q", self.rows)

    def test_empty_input_makes_no_request(self):
        with self.post() as post:
            self.assertEqual(engine.rerank_context("q", []), [])
        post.assert_not_called()


class UploadValidationTests(unittest.TestCase):
    def code(self, name, data):
        with self.assertRaises(ApiError) as caught:
            ingestion.validate_upload(name, data)
        return caught.exception.code

    def test_accepts_supported_files(self):
        self.assertEqual(ingestion.validate_upload("a.pdf", b"%PDF-1.7 x")[1], "application/pdf")
        self.assertEqual(ingestion.validate_upload("a.md", b"# hi")[1], "text/markdown")

    def test_rejects_bad_files(self):
        self.assertEqual(self.code("a.exe", b"x"), "unsupported_file_type")
        self.assertEqual(self.code("a.pdf", b""), "empty_file")
        self.assertEqual(self.code("a.pdf", b"<html>"), "invalid_pdf")
        self.assertEqual(self.code("a.txt", b"\xff\xfe\xff"), "invalid_text")

    def test_rejects_oversized_files(self):
        with mock.patch.object(ingestion, "MAX_UPLOAD_BYTES", 4):
            self.assertEqual(self.code("a.txt", b"12345"), "file_too_large")

    def test_filename_cannot_choose_a_path(self):
        self.assertEqual(ingestion.safe_filename("../../etc/passwd.txt"), "passwd.txt")
        self.assertEqual(ingestion.safe_filename("..\\..\\win.pdf"), "win.pdf")
        self.assertEqual(ingestion.safe_filename("a<b>.pdf"), "a_b_.pdf")

    def test_normalize_removes_nul_bytes(self):
        self.assertEqual(ingestion.normalize_text("a\x00b  c\r\n\r\n\r\n\r\nd"), "ab c\n\nd")

    def test_corrupt_pdf_and_empty_text_fail_clearly(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = Path(folder) / "bad.pdf"
            bad.write_bytes(b"%PDF-1.7 broken")
            with self.assertRaises(ingestion.IngestionError):
                ingestion.extract_pages(bad, "application/pdf")
            blank = Path(folder) / "blank.txt"
            blank.write_text("  \n ")
            with self.assertRaises(ingestion.IngestionError):
                ingestion.extract_pages(blank, "text/plain")

    def test_chunks_keep_page_numbers(self):
        pages = [ingestion.Page(1, "one"), ingestion.Page(3, "three")]
        chunks = ingestion.build_chunks(
            pages, None, lambda text, tok, chunk_size, overlap: [text], 100, 10
        )
        self.assertEqual([c["page_number"] for c in chunks], [1, 3])

    def test_wrong_embedding_dimension_is_rejected(self):
        model = mock.Mock()
        model.encode.return_value = np.zeros((1, 10))
        with self.assertRaises(ingestion.IngestionError):
            ingestion.embed_chunks([{"content": "x"}], model)

    def test_remove_file_stays_inside_upload_directory(self):
        with tempfile.TemporaryDirectory() as folder, tempfile.NamedTemporaryFile() as outside:
            with mock.patch.object(ingestion, "UPLOAD_DIR", Path(folder)):
                ingestion.remove_file(outside.name)
            self.assertTrue(Path(outside.name).exists())


class ChunkingTests(unittest.TestCase):
    class Uncased:
        def encode(self, text, add_special_tokens=False):
            return text.lower().split()

        def __call__(self, text, add_special_tokens=False, return_offsets_mapping=True):
            offsets, position = [], 0
            for word in text.split():
                start = text.index(word, position)
                position = start + len(word)
                offsets.append((start, position))
            return {"offset_mapping": offsets}

    def test_original_case_survives_an_uncased_tokenizer(self):
        chunks = chunk_text("Tamsin Okoro. " * 40, self.Uncased(), chunk_size=20, overlap=4)
        self.assertGreater(len(chunks), 1)
        self.assertTrue(all("Tamsin Okoro." in chunk for chunk in chunks))

    def test_long_sentence_is_split_on_word_boundaries(self):
        sentence = " ".join(f"Word{index}" for index in range(100))
        chunks = chunk_text(sentence, self.Uncased(), chunk_size=30, overlap=5)
        self.assertTrue(all(len(chunk.split()) <= 32 for chunk in chunks))
        self.assertIn("Word99", chunks[-1])

    def test_invalid_configuration_is_rejected(self):
        with self.assertRaises(ValueError):
            chunk_text("x", self.Uncased(), chunk_size=10, overlap=10)


class SettingsValidationTests(unittest.TestCase):
    def assert_invalid(self, **changes):
        with self.assertRaises(ApiError):
            settings_repo.validate({**config.DEFAULT_SETTINGS, **changes})

    def test_defaults_are_valid(self):
        self.assertEqual(settings_repo.validate(dict(config.DEFAULT_SETTINGS))["chunk_size"], 180)

    def test_rejects_out_of_range_values(self):
        self.assert_invalid(chunk_size=500)
        self.assert_invalid(chunk_overlap=200)
        self.assert_invalid(chunk_size=60, chunk_overlap=60)
        self.assert_invalid(final_context_k=0)
        self.assert_invalid(final_context_k=True)
        self.assert_invalid(default_profile_id="nope")
        self.assert_invalid(rerank_enabled="yes")


class ProfileTests(unittest.TestCase):
    def test_required_profiles_exist(self):
        for name, mode, depth, weights in (
            ("A_vector_top10", "vector", 10, None),
            ("B_vector_top18", "vector", 18, None),
            ("C_rrf1_1_top18", "rrf", 18, (1, 1)),
            ("D_rrf3_1_top18", "rrf", 18, (3, 1)),
        ):
            profile = config.PROFILES[name]
            self.assertEqual((profile.mode, profile.depth), (mode, depth))
            if weights:
                self.assertEqual((profile.vector_weight, profile.keyword_weight), weights)

    def test_default_keeps_current_pipeline_behaviour(self):
        profile = config.PROFILES["rrf3_1_top10"]
        self.assertEqual((profile.depth, profile.candidate_k), (10, 18))
        self.assertEqual((engine.RRF_VECTOR_WEIGHT, engine.RRF_KEYWORD_WEIGHT), (3.0, 1.0))


class SecurityTests(unittest.TestCase):
    def request(self, header=None):
        item = mock.Mock()
        item.headers = {"authorization": header} if header else {}
        return item

    def test_token_is_optional_by_default(self):
        with mock.patch.object(config, "API_TOKEN", ""):
            require_token(self.request())

    def test_token_is_enforced_when_set(self):
        with mock.patch.object(config, "API_TOKEN", "secret"):
            require_token(self.request("Bearer secret"))
            for bad in (None, "Bearer wrong", "secret"):
                with self.assertRaises(ApiError):
                    require_token(self.request(bad))

    def test_rate_limiter(self):
        limiter = RateLimiter(2, 60)
        limiter.check("a")
        limiter.check("a")
        with self.assertRaises(ApiError):
            limiter.check("a")
        limiter.check("b")


class ChatHelperTests(unittest.TestCase):
    def test_reranker_failure_degrades_visibly(self):
        rows = [{"id": 1, "content": "a", "similarity": 0.9}, {"id": 2, "content": "b", "similarity": 0.8}]
        with mock.patch.object(engine, "rerank_context", side_effect=requests.Timeout()):
            ranked, status = chat_service._rerank("q", rows, 1, True)
        self.assertEqual(status, "failed_used_retrieval_order")
        self.assertEqual([row["id"] for row in ranked], [1])
        self.assertIsNone(ranked[0]["rerank_score"])

    def test_rerank_can_be_disabled(self):
        rows = [{"id": 1, "content": "a", "similarity": 0.9}]
        with mock.patch.object(engine, "rerank_context") as rerank:
            _ranked, status = chat_service._rerank("q", rows, 1, False)
        rerank.assert_not_called()
        self.assertEqual(status, "disabled")

    def test_provider_errors_become_safe_api_errors(self):
        request = mock.Mock()
        cases = (
            (openai.APITimeoutError(request=request), 504, "model_timeout"),
            (ValueError("LLM returned an empty answer."), 502, "model_invalid_response"),
            (openai.APIConnectionError(request=request), 503, "model_timeout"),
        )
        for error, status, _code in cases:
            with self.assertRaises(ApiError) as caught:
                chat_service._call_model(mock.Mock(side_effect=error))
            self.assertIn(caught.exception.status_code, (status, 503, 504))
            self.assertNotIn("nvapi", caught.exception.message)

    def test_evidence_follows_output_masking(self):
        with mock.patch.dict(os.environ, {"RAG_REDACT_OUTPUT": "email"}):
            self.assertIn("[REDACTED_EMAIL]", chat_service.redact_content("Mail a@b.co now"))
        with mock.patch.dict(os.environ, {"RAG_REDACT_OUTPUT": ""}):
            self.assertIn("a@b.co", chat_service.redact_content("Mail a@b.co now"))

    def test_generate_answer_uses_given_prompt_or_the_evaluated_one(self):
        reply = mock.Mock()
        reply.choices = [mock.Mock(message=mock.Mock(content="ok"))]
        reply.usage = None
        with mock.patch.object(engine.llm.chat.completions, "create", return_value=reply) as create:
            engine.generate_answer("q", [{"id": 1, "content": "c"}], system_prompt="CUSTOM")
            self.assertEqual(create.call_args.kwargs["messages"][0]["content"], "CUSTOM")
            engine.generate_answer("q", [{"id": 1, "content": "c"}])
            self.assertIn("resume assistant", create.call_args.kwargs["messages"][0]["content"])


class ReportTests(unittest.TestCase):
    """These read the saved reports, or skip when the private files are absent."""

    def setUp(self):
        if not (config.REPORTS_DIR / "golden_v1_generation_report.json").exists():
            self.skipTest("Saved reports are not present")

    def test_saved_generation_values_are_passed_through(self):
        rows = reports.get_evaluation("generation")["summary"]["configurations"]
        self.assertEqual(len(rows), 3)
        for row in rows:
            self.assertEqual(row["faithfulness_micro"], 1.0)
            self.assertAlmostEqual(row["answer_relevancy_mean"], 4.9697, places=3)
            self.assertAlmostEqual(row["expected_point_coverage_micro"], 0.9535, places=3)
            self.assertAlmostEqual(row["citation_support_macro"], 0.8611, places=3)
            self.assertEqual(row["citation_id_validity_micro"], 1.0)
            self.assertEqual(row["correct_abstention_rate"], 1.0)
            self.assertEqual(row["correct_abstentions"], 6)

    def test_labels_keep_evaluation_versions_apart(self):
        labels = {item["id"]: item["label"] for item in reports.list_evaluations()}
        self.assertEqual(labels["generation"], "ORIGINAL_EVALUATION")
        self.assertEqual(labels["citation_corrections"], "OFFLINE_ANNOTATION_CORRECTION")
        self.assertEqual(labels["ragas"], "NEW_EVALUATION")

    def test_p013_stays_unapproved(self):
        summary = reports.get_evaluation("citation_corrections")["summary"]
        self.assertEqual(summary["human_review"]["status"], "NEEDS_HUMAN_APPROVAL")
        self.assertEqual(summary["corrected_instances"], 18)
        self.assertEqual(summary["remaining_unsupported_instances"], 2)

    def test_comparison_matches_saved_benchmarks(self):
        rows = {row["id"]: row for row in reports.experiments_comparison()["rows"]}
        self.assertEqual(rows["retrieval:rrf_3_1"]["mrr_at_10"], 0.9571)
        self.assertAlmostEqual(rows["reranking_deep:vector_top18"]["precision_at_3"], 0.5455, places=3)

    def test_missing_report_is_unavailable_not_zero(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(config, "REPORTS_DIR", Path(folder)):
            result = reports.get_evaluation("generation")
            self.assertFalse(result["available"])
            self.assertIsNone(result["summary"])
            self.assertEqual(reports.experiments_comparison()["rows"], [])

    def test_comparison_makes_no_network_calls(self):
        with mock.patch.object(engine.requests, "post") as post, \
                mock.patch.object(engine.llm.chat.completions, "create") as create:
            reports.experiments_comparison()
        post.assert_not_called()
        create.assert_not_called()


if __name__ == "__main__":
    unittest.main()
