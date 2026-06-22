from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from graph_visualizer import export_interactive_html


class GraphVisualizerTests(unittest.TestCase):
    def test_exports_embedded_interactive_graph(self) -> None:
        graph = {
            "directed": True,
            "multigraph": False,
            "graph": {},
            "nodes": [{"id": "auth.py", "functions": ["verify_token"], "classes": [], "imports": [], "docstring": "Auth"}],
            "links": [],
        }
        with tempfile.TemporaryDirectory() as directory:
            output = export_interactive_html(graph, Path(directory) / "graph.html")
            html = output.read_text(encoding="utf-8")
            self.assertIn("Architectural Memory Graph", html)
            self.assertIn('"id": "auth.py"', html)
            self.assertIn("verify_token", html)


if __name__ == "__main__":
    unittest.main()
