from __future__ import annotations

import tempfile
import unittest
import json
from pathlib import Path

from compare_workspaces import analyze_enter_session, analyze_project


class CompareWorkspacesTests(unittest.TestCase):
    def test_analyzes_project_code_and_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "sample"
            root.mkdir()
            (root / "app.py").write_text(
                "import service\n\ndef main():\n    return service.run()\n", encoding="utf-8"
            )
            (root / "service.py").write_text(
                "class Service:\n    pass\n\ndef run():\n    return True\n", encoding="utf-8"
            )
            metrics = analyze_project(root)
        self.assertEqual(metrics.python_files, 2)
        self.assertEqual(metrics.modules, 2)
        self.assertEqual(metrics.dependency_edges, 1)
        self.assertEqual(metrics.functions, 2)
        self.assertEqual(metrics.classes, 1)

    def test_sums_enter_provider_usage_and_counts_real_prompts(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            session = Path(directory) / "session-123.jsonl"
            records = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "<system-reminder>Injected</system-reminder>"},
                        {"type": "text", "text": "Build the feature"},
                    ],
                },
                {
                    "role": "assistant",
                    "content": [],
                    "usage": {
                        "input_tokens": 2,
                        "cache_creation_input_tokens": 100,
                        "cache_read_input_tokens": 20,
                        "output_tokens": 30,
                    },
                },
                {
                    "role": "user",
                    "content": [{"type": "tool_result", "content": "done"}],
                },
                {"role": "user", "content": [{"type": "text", "text": "Extend it"}]},
                {
                    "role": "assistant",
                    "content": [],
                    "usage": {
                        "input_tokens": 3,
                        "cache_read_input_tokens": 120,
                        "output_tokens": 10,
                    },
                },
            ]
            session.write_text(
                "\n".join(json.dumps(record) for record in records), encoding="utf-8"
            )
            usage = analyze_enter_session(session)

        self.assertEqual(usage.user_prompts, 2)
        self.assertEqual(usage.model_calls, 2)
        self.assertEqual(usage.model_input_tokens, 245)
        self.assertEqual(usage.output_tokens, 40)
        self.assertEqual(usage.total_tokens, 285)
        self.assertEqual([prompt.total_tokens for prompt in usage.prompt_usage], [152, 133])


if __name__ == "__main__":
    unittest.main()
