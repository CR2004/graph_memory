from __future__ import annotations

import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from architecture_cli import build_parser, execute
from enter_integration import parcle_project_id


class ArchitectureCliTests(unittest.TestCase):
    def test_graph_command_uses_shared_enter_integration(self) -> None:
        args = build_parser().parse_args(["graph"])
        with tempfile.TemporaryDirectory() as directory:
            project = Path(directory)
            (project / "api.py").write_text("import storage\n", encoding="utf-8")
            (project / "storage.py").write_text("DATA = []\n", encoding="utf-8")
            with patch("enter_integration.PROJECT_ROOT", project):
                result = execute(args)
        self.assertEqual(result["modules"], ["api.py", "storage.py"])
        self.assertEqual(
            result["dependencies"],
            [{"source": "api.py", "target": "storage.py"}],
        )

    def test_status_reports_configured_project(self) -> None:
        args = build_parser().parse_args(["status"])
        result = execute(args)
        self.assertEqual(result["project_id"], parcle_project_id())
        self.assertEqual(result["contribution_mode"], "architectural")


if __name__ == "__main__":
    unittest.main()
