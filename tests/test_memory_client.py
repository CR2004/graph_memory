from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import Mock

from memory_client import ParcleMemory
from parcle.exceptions import NotFoundError


class ParcleMemoryTests(unittest.TestCase):
    def test_record_decision_sends_conversation_and_returns_session(self) -> None:
        client = Mock()
        client.ingest_dialog.return_value = SimpleNamespace(session_id="session-123")
        memory = ParcleMemory(project_id="test-project", client=client)

        session_id = memory.record_decision(
            module="services/budgets.py",
            prompt_description="Add monthly budgets",
            decision="Keep calculations in a budget service",
            rationale="Routes should remain thin",
        )

        self.assertEqual(session_id, "session-123")
        client.create_user.assert_called_once_with(
            user_id="test-project", name="test-project"
        )
        client.ingest_dialog.assert_called_once_with(
            user_id="test-project",
            messages=[
                {"role": "user", "content": "Add monthly budgets"},
                {
                    "role": "assistant",
                    "content": (
                        "Created services/budgets.py. Decision: Keep calculations in a "
                        "budget service. Rationale: Routes should remain thin."
                    ),
                },
            ],
        )

    def test_query_normalizes_real_sdk_response(self) -> None:
        client = Mock()
        client.search.return_value = SimpleNamespace(
            answer="Extend services/budgets.py.",
            confidence=0.86,
            citations=[SimpleNamespace(type="session", id="session-123")],
        )
        memory = ParcleMemory(project_id="test-project", client=client)

        result = memory.query("Add threshold alerts")

        client.search.assert_called_once_with(
            user_id="test-project", query="Add threshold alerts"
        )
        self.assertEqual(
            result,
            {
                "match_found": True,
                "confidence": 0.86,
                "answer": "Extend services/budgets.py.",
                "citations": [{"type": "session", "id": "session-123"}],
            },
        )

    def test_record_raw_event_keeps_control_memory_unstructured(self) -> None:
        client = Mock()
        client.ingest_dialog.return_value = SimpleNamespace(session_id="raw-session")
        memory = ParcleMemory(project_id="control", client=client)
        session_id = memory.record_raw_event(
            "Add budgets", "Implemented request. Changed files: app.py."
        )
        self.assertEqual(session_id, "raw-session")
        client.create_user.assert_called_once_with(user_id="control", name="control")
        client.ingest_dialog.assert_called_once_with(
            user_id="control",
            messages=[
                {"role": "user", "content": "Add budgets"},
                {
                    "role": "assistant",
                    "content": "Implemented request. Changed files: app.py.",
                },
            ],
        )

    def test_query_applies_confidence_threshold(self) -> None:
        client = Mock()
        client.search.return_value = SimpleNamespace(
            answer="Weak match", confidence=0.3, citations=[]
        )
        memory = ParcleMemory(
            project_id="test-project", confidence_threshold=0.5, client=client
        )
        self.assertFalse(memory.query("Something new")["match_found"])

    def test_unknown_project_is_normalized_as_empty_memory(self) -> None:
        client = Mock()
        client.search.side_effect = NotFoundError(
            "Unknown user", status_code=404, code="user_not_found"
        )
        memory = ParcleMemory(project_id="fresh-project", client=client)
        result = memory.query("First feature")
        self.assertFalse(result["match_found"])
        self.assertEqual(result["confidence"], 0.0)
        self.assertEqual(result["citations"], [])


if __name__ == "__main__":
    unittest.main()
