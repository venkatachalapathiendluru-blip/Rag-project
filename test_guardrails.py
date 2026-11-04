import json
from pathlib import Path
import unittest

from guardrails import (
    MAX_QUESTION_CHARS,
    UNTRUSTED_NOTICE,
    check_input,
    check_output,
    redact_pii,
    sanitize_chunks,
)
from redteam_cases import (
    BENIGN_QUESTIONS,
    DIRECT_ATTACKS,
    INDIRECT_ATTACK_DOCUMENTS,
)


class InputGuardrailTests(unittest.TestCase):
    def test_direct_attacks_are_blocked(self):
        missed = [q for q in DIRECT_ATTACKS if check_input(q).allowed]
        self.assertEqual(missed, [])

    def test_benign_questions_pass(self):
        blocked = [q for q in BENIGN_QUESTIONS if not check_input(q).allowed]
        self.assertEqual(blocked, [])

    def test_golden_dataset_questions_pass(self):
        path = Path(__file__).with_name("golden_dataset_v1_reviewed.json")
        if not path.exists():
            self.skipTest("the test set holds personal resume details and is not published")
        questions = json.loads(path.read_text(encoding="utf-8"))["questions"]
        blocked = [
            q["question"] for q in questions if not check_input(q["question"]).allowed
        ]
        self.assertEqual(blocked, [])

    def test_empty_and_oversized_questions_are_blocked(self):
        self.assertEqual(check_input("  ").reasons, ["empty_question"])
        self.assertEqual(
            check_input("a" * (MAX_QUESTION_CHARS + 1)).reasons,
            ["question_too_long"],
        )


class ContextGuardrailTests(unittest.TestCase):
    def test_instructions_in_documents_are_removed(self):
        rows = [
            {"id": index, "content": text}
            for index, text in enumerate(INDIRECT_ATTACK_DOCUMENTS)
        ]
        sanitized, flagged = sanitize_chunks(rows)
        self.assertEqual(flagged, [row["id"] for row in rows])
        self.assertTrue(all(UNTRUSTED_NOTICE in row["content"] for row in sanitized))

    def test_normal_documents_and_original_rows_are_unchanged(self):
        rows = [{"id": 1, "content": "Built REST APIs with Django and FastAPI."}]
        sanitized, flagged = sanitize_chunks(rows)
        self.assertEqual(flagged, [])
        self.assertEqual(sanitized, rows)
        self.assertIsNot(sanitized[0], rows[0])


class OutputGuardrailTests(unittest.TestCase):
    def test_system_prompt_leak_is_blocked(self):
        answer, reasons = check_output(
            "Sure: You are a helpful resume assistant. Do not invent experience."
        )
        self.assertEqual(reasons, ["system_prompt_leak"])
        self.assertNotIn("resume assistant", answer)

    def test_secrets_are_masked_but_contact_details_stay_by_default(self):
        answer, reasons = check_output(
            "Key nvapi-abcdefghijklmnop, mail a.person@example.com"
        )
        self.assertIn("[REDACTED_API_KEY]", answer)
        self.assertIn("a.person@example.com", answer)
        self.assertEqual(reasons, ["redacted_api_key"])

    def test_pii_kinds_are_masked(self):
        text = (
            "a.person@example.com +91 98765 43210 ABCDE1234F 2345 6789 0123 "
            "sk-ant-abcdefghijklmnop"
        )
        redacted, counts = redact_pii(text)
        self.assertEqual(
            counts,
            {"api_key": 1, "email": 1, "aadhaar": 1, "pan": 1, "phone": 1},
        )
        self.assertNotRegex(redacted, r"\d{4}")

    def test_ordinary_numbers_are_not_masked(self):
        text = "Handled 158 endpoints in 2023, MRR 0.957, ID 1234567."
        self.assertEqual(redact_pii(text), (text, {}))


if __name__ == "__main__":
    unittest.main()
