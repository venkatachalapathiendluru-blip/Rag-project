import unittest
from unittest import mock

from fastapi.testclient import TestClient

import api


class ApiTests(unittest.TestCase):
    def setUp(self):
        api._requests_by_client.clear()
        self.client = TestClient(api.app)

    def test_health_and_demo_page(self):
        self.assertEqual(self.client.get("/healthz").json(), {"status": "ok"})
        self.assertIn("Hybrid RAG Assistant", self.client.get("/").text)

    def test_chat_returns_answer(self):
        with mock.patch.object(api, "rag_chat", return_value="Answer [Chunk ID: 1]"):
            response = self.client.post("/chat", json={"question": "Skills?"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"answer": "Answer [Chunk ID: 1]"})

    def test_invalid_questions_are_rejected(self):
        self.assertEqual(self.client.post("/chat", json={"question": ""}).status_code, 422)
        long_question = {"question": "a" * (api.MAX_QUESTION_CHARS + 1)}
        self.assertEqual(self.client.post("/chat", json=long_question).status_code, 422)

    def test_provider_errors_are_not_exposed(self):
        with mock.patch.object(api, "rag_chat", side_effect=RuntimeError("key nvapi-123")):
            response = self.client.post("/chat", json={"question": "Skills?"})

        self.assertEqual(response.status_code, 503)
        self.assertNotIn("nvapi", response.text)

    def test_rate_limit(self):
        with mock.patch.object(api, "rag_chat", return_value="ok"):
            codes = [
                self.client.post("/chat", json={"question": "Skills?"}).status_code
                for _ in range(api.RATE_LIMIT_REQUESTS + 1)
            ]

        self.assertEqual(codes[-1], 429)
        self.assertEqual(set(codes[:-1]), {200})


if __name__ == "__main__":
    unittest.main()
