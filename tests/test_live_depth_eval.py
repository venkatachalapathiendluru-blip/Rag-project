"""The depth comparison must reuse results and refuse mismatched inputs. No model is called."""

import unittest

import evaluate_live_pipeline_depths as depth


def question(question_id, answerability="answerable"):
    return {
        "question_id": question_id, "question": f"q {question_id}",
        "answerability": answerability, "relevant_chunk_ids": [1],
        "expected_answer_points": ["p"], "why_unanswerable": "w", "expected_behavior": "e",
    }


def frozen(after_10, after_18, question_id="Q1"):
    before = [1, 2, 3, 4]
    return {
        "live_rrf3_1_top10": {question_id: {"before_ids": before, "after_ids": after_10, "latency_ms": 5}},
        "live_rrf3_1_top18": {question_id: {"before_ids": before, "after_ids": after_18, "latency_ms": 9}},
    }


def retrieve(_question, _profile):
    return [{"id": i, "content": f"chunk {i}"} for i in (1, 2, 3, 4)]


def fake_stages(calls):
    def stage(name, **extra):
        def run(*_args):
            calls.append(name)
            return {"status": "OK", "usage": {"total_tokens": 10}, "latency_ms": 1, **extra}
        return run

    return {
        "generate": stage("generate", answer="a"),
        "citations": lambda *_a: {"citation_id_validity": {}},
        "v3": stage("v3"), "coverage": stage("coverage"), "abstention": stage("abstention"),
    }


class DepthComparison(unittest.TestCase):
    def test_identical_contexts_share_calls(self):
        plan = depth.build_plan([question("Q1")], frozen([1, 2, 3], [1, 2, 3]), retrieve)
        calls = []
        entries = depth.evaluate(plan, fake_stages(calls), {}, lambda: None)
        self.assertEqual(calls, ["generate", "v3", "coverage"])
        self.assertEqual(len(entries), 2)
        self.assertEqual(depth.count_planned_calls(plan)["total"], 3)

    def test_different_contexts_are_each_run(self):
        plan = depth.build_plan([question("Q1")], frozen([1, 2, 3], [1, 2, 4]), retrieve)
        calls = []
        depth.evaluate(plan, fake_stages(calls), {}, lambda: None)
        self.assertEqual(len(calls), 6)

    def test_rerun_only_repeats_failures(self):
        plan = depth.build_plan([question("Q1")], frozen([1, 2, 3], [1, 2, 3]), retrieve)
        checkpoint, calls = {}, []
        stages = fake_stages(calls)
        stages["v3"] = lambda *_a: {"status": "ERROR"}
        entries = depth.evaluate(plan, stages, checkpoint, lambda: None)
        self.assertEqual(entries[0]["status"], "FAILED")
        calls.clear()
        entries = depth.evaluate(plan, fake_stages(calls), checkpoint, lambda: None)
        self.assertEqual(calls, ["v3"])
        self.assertEqual(entries[0]["status"], "OK")

    def test_unanswerable_uses_abstention_judge(self):
        plan = depth.build_plan([question("Q1", "unanswerable")], frozen([1, 2, 3], [1, 2, 3]), retrieve)
        calls = []
        depth.evaluate(plan, fake_stages(calls), {}, lambda: None)
        self.assertEqual(calls, ["generate", "abstention"])

    def test_mismatched_saved_candidates_stop_the_run(self):
        saved = frozen([1, 2, 3], [1, 2, 3])
        saved["live_rrf3_1_top18"]["Q1"]["before_ids"] = [9, 9]
        with self.assertRaises(ValueError):
            depth.build_plan([question("Q1")], saved, retrieve)


if __name__ == "__main__":
    unittest.main()
