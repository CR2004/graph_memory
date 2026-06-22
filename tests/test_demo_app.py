from __future__ import annotations

import unittest
from unittest.mock import patch
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

import demo_app


class DemoAppTests(unittest.TestCase):
    def test_sample_is_self_consistent_and_includes_stage_graph(self) -> None:
        sample = demo_app.sample_payload()

        cost = sample["token_cost"]
        self.assertEqual(cost["focused_total"], cost["focused_change_packet"] + cost["recommended_source"])
        self.assertEqual(cost["difference"], cost["full_repository"] - cost["focused_total"])
        self.assertIn("app/routes.py", sample["graph"]["modules"])
        self.assertTrue(sample["graph"]["dependencies"])
        self.assertEqual(sample["change_packet"]["capability"]["status"], "likely_exists")

    def test_status_reports_active_condition_without_credentials(self) -> None:
        with patch(
            "demo_app.graph_payload",
            return_value={"modules": [], "dependencies": [], "module_mtimes": {}},
        ):
            status = demo_app.status_payload()
        self.assertEqual(status["mode"], "architectural")
        self.assertEqual(status["project"], "hackathon_workspace")
        self.assertIn("enter", status["enter_command"])

    def test_plans_against_live_workspace_without_starting_enter(self) -> None:
        result_json = json.dumps({"token_cost": {"focused_total": 1200}})
        completed = SimpleNamespace(returncode=0, stdout=result_json, stderr="")
        graph = {"modules": ["app/service.py"], "dependencies": [], "module_mtimes": {}}
        with (
            patch("demo_app.subprocess.run", return_value=completed) as run,
            patch("demo_app.graph_payload", return_value=graph),
        ):
            result = demo_app.plan_live_workspace("Add summaries")
        self.assertEqual(result["request"], "Add summaries")
        self.assertEqual(result["graph"], graph)
        self.assertIn("architecture_cli.py", run.call_args.args[0][1])

    def test_reads_actual_provider_usage_from_new_enter_session(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            sessions = Path(directory)
            session = sessions / "session-live.jsonl"
            session.write_text(
                "\n".join(
                    [
                        json.dumps({"usage": {"input_tokens": 2, "cache_creation_input_tokens": 100, "output_tokens": 20}}),
                        json.dumps({"usage": {"input_tokens": 2, "cache_read_input_tokens": 100, "output_tokens": 10}}),
                    ]
                ),
                encoding="utf-8",
            )
            with patch("demo_app._session_directory", return_value=sessions):
                usage = demo_app.usage_since(Path("unused"), started_at=0)

        self.assertIsNotNone(usage)
        self.assertEqual(usage["model_calls"], 2)
        self.assertEqual(usage["model_input_tokens"], 204)
        self.assertEqual(usage["total_tokens"], 234)


if __name__ == "__main__":
    unittest.main()
