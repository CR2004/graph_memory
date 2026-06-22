from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from enter_integration import (
    check_architectural_memory,
    get_architecture_graph,
    plan_architectural_change,
)


class EnterIntegrationTests(unittest.TestCase):
    def test_raw_control_still_queries_parcle(self) -> None:
        with patch.dict(os.environ, {"ARCH_MEMORY_MODE": "raw_parcle"}):
            with patch("enter_integration.ParcleMemory") as parcle:
                parcle.return_value.query.return_value = {
                    "match_found": False,
                    "confidence": 0.1,
                    "answer": "Only generic prompt history was found.",
                    "citations": [],
                }
                result = check_architectural_memory("Add a duplicate service")
        parcle.assert_called_once()
        parcle.return_value.query.assert_called_once_with("Add a duplicate service")
        self.assertEqual(result["contribution_mode"], "raw_parcle")
        self.assertFalse(result["match_found"])

    def test_graph_context_exposes_fixture_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "app.py").write_text(
                "from service import run\n\ndef main():\n    return run()\n",
                encoding="utf-8",
            )
            (project / "service.py").write_text(
                "def run():\n    return 'ok'\n", encoding="utf-8"
            )
            with patch("enter_integration.PROJECT_ROOT", project):
                result = get_architecture_graph()
        self.assertEqual(result["modules"], ["app.py", "service.py"])
        self.assertEqual(
            result["dependencies"],
            [{"source": "app.py", "target": "service.py"}],
        )

    def test_combined_planner_ranks_targets_and_expands_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "routes.py").write_text(
                "import service\n\ndef list_expenses():\n    return service.list_expenses()\n",
                encoding="utf-8",
            )
            (project / "service.py").write_text(
                "import repository\n\ndef summarize_by_category():\n    return repository.sum_by_category()\n",
                encoding="utf-8",
            )
            (project / "repository.py").write_text(
                "def sum_by_category():\n    return {}\n", encoding="utf-8"
            )
            memory_result = {
                "match_found": True,
                "confidence": 0.9,
                "answer": "Keep category aggregation in service.py and repository.py.",
                "citations": [{"type": "session", "id": "sess_test"}],
            }
            with (
                patch.dict(os.environ, {"ARCH_MEMORY_MODE": "architectural"}),
                patch("enter_integration.PROJECT_ROOT", project),
                patch("enter_integration.ParcleMemory") as parcle,
            ):
                parcle.return_value.query.return_value = memory_result
                result = plan_architectural_change(
                    "Add a category spending summary endpoint",
                    max_targets=3,
                    max_initial_files=3,
                    max_source_tokens=500,
                )

        parcle.return_value.query.assert_called_once_with(
            "Add a category spending summary endpoint"
        )
        targets = [
            item["module"]
            for item in result["change_packet"]["likely_change_targets"]
        ]
        self.assertIn("service.py", targets)
        self.assertLessEqual(
            len(result["change_packet"]["recommended_reads"]), 2
        )
        self.assertEqual(
            result["change_packet"]["capability"]["status"], "likely_exists"
        )
        self.assertTrue(result["change_packet"]["neighbor_hints"])
        self.assertIn("recommended_source", result["token_cost"])
        self.assertEqual(
            result["token_cost"]["focused_total"],
            result["token_cost"]["focused_change_packet"]
            + result["token_cost"]["recommended_source"],
        )


if __name__ == "__main__":
    unittest.main()
