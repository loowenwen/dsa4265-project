import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app
from app.services.chat import chat_service


class ChatApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)
        with chat_service._SESSION_LOCK:
            chat_service._SESSIONS.clear()

    def tearDown(self) -> None:
        with chat_service._SESSION_LOCK:
            chat_service._SESSIONS.clear()

    def _mock_rag_result(self) -> dict:
        return {
            "context": "[Source 1] Chunk ID: policy_006\nText: LTV policy text",
            "final_answer": "Grounded fallback from retrieval.",
            "reranked_docs": [
                {
                    "chunk_id": "policy_006",
                    "title": "Residential mortgage LTV policy",
                    "section_header": "RESIDENTIAL MORTGAGE UNDERWRITING PRACTICES AND PROCEDURES",
                    "text": "For residential mortgage loans, lenders should establish and adhere to LTV ratios.",
                },
                {
                    "chunk_id": "policy_007",
                    "title": "Debt serviceability assessment",
                    "section_header": "RESIDENTIAL MORTGAGE UNDERWRITING PRACTICES AND PROCEDURES",
                    "text": "Licensees are required to appropriately assess borrowers' ability to service and repay.",
                },
            ],
        }

    def test_chat_creates_session_and_returns_citations(self) -> None:
        with patch("app.services.chat.chat_service._retrieve_policy_result", return_value=self._mock_rag_result()):
            with patch("app.services.chat.chat_service._call_chat_llm", return_value="Use prudent LTV and affordability checks.\n\nSources: policy_006"):
                with patch("app.services.chat.chat_service.settings.OPENROUTER_API_KEY", "test-key"):
                    response = self.client.post(
                        "/api/v1/chat",
                        json={"message": "How should we treat high LTV applications?"},
                    )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["session_id"])
        self.assertTrue(payload["llm_used"])
        self.assertEqual(payload["memory"]["turn_count"], 1)
        self.assertFalse(payload["memory"]["truncated"])
        self.assertGreaterEqual(len(payload["citations"]), 1)
        self.assertEqual(payload["citations"][0]["chunk_id"], "policy_006")

    def test_chat_reuses_session_memory(self) -> None:
        with patch("app.services.chat.chat_service._retrieve_policy_result", return_value=self._mock_rag_result()):
            with patch("app.services.chat.chat_service._call_chat_llm", return_value="Manual review may be needed.\n\nSources: policy_007"):
                with patch("app.services.chat.chat_service.settings.OPENROUTER_API_KEY", "test-key"):
                    first = self.client.post(
                        "/api/v1/chat",
                        json={"message": "What about debt serviceability?"},
                    )
                    session_id = first.json()["session_id"]

                    second = self.client.post(
                        "/api/v1/chat",
                        json={
                            "message": "And if income is unstable?",
                            "session_id": session_id,
                        },
                    )

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json()["session_id"], session_id)
        self.assertEqual(second.json()["memory"]["turn_count"], 2)

    def test_chat_enforces_memory_turn_cap(self) -> None:
        with patch("app.services.chat.chat_service._retrieve_policy_result", return_value=self._mock_rag_result()):
            with patch("app.services.chat.chat_service._call_chat_llm", return_value="Answer.\n\nSources: policy_006"):
                with patch("app.services.chat.chat_service.settings.OPENROUTER_API_KEY", "test-key"):
                    with patch("app.services.chat.chat_service.settings.CHAT_MEMORY_MAX_TURNS", 2):
                        first = self.client.post("/api/v1/chat", json={"message": "Q1"})
                        session_id = first.json()["session_id"]

                        self.client.post(
                            "/api/v1/chat",
                            json={"message": "Q2", "session_id": session_id},
                        )
                        third = self.client.post(
                            "/api/v1/chat",
                            json={"message": "Q3", "session_id": session_id},
                        )

        self.assertEqual(third.status_code, 200)
        self.assertEqual(third.json()["memory"]["turn_count"], 2)
        self.assertTrue(third.json()["memory"]["truncated"])

    def test_chat_fallback_when_llm_unavailable(self) -> None:
        with patch("app.services.chat.chat_service._retrieve_policy_result", return_value=self._mock_rag_result()):
            with patch("app.services.chat.chat_service.settings.OPENROUTER_API_KEY", None):
                response = self.client.post(
                    "/api/v1/chat",
                    json={"message": "What is the policy guidance for rent applicants?"},
                )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertFalse(payload["llm_used"])
        self.assertIn("Sources:", payload["answer"])

    def test_chat_rejects_empty_message(self) -> None:
        response = self.client.post(
            "/api/v1/chat",
            json={"message": "   "},
        )

        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
