from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from ast_extractor import extract_python_file


class ExtractPythonFileTests(unittest.TestCase):
    def test_extracts_top_level_architecture(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module = root / "service.py"
            module.write_text(
                '\"\"\"Service docs.\"\"\"\n'
                "import time\nfrom collections import defaultdict\n\n"
                "def run():\n    pass\n\nclass Worker:\n    pass\n",
                encoding="utf-8",
            )

            info = extract_python_file(module, project_root=root)

            self.assertEqual(info.module, "service.py")
            self.assertEqual(info.functions, ["run"])
            self.assertEqual(info.classes, ["Worker"])
            self.assertEqual(info.imports, ["time", "collections.defaultdict"])
            self.assertEqual(info.docstring, "Service docs.")

    def test_ignores_nested_definitions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module = root / "nested.py"
            module.write_text(
                "def outer():\n    def inner():\n        pass\n    return inner\n",
                encoding="utf-8",
            )
            info = extract_python_file(module, project_root=root)
            self.assertEqual(info.functions, ["outer"])

    def test_preserves_relative_imports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            module = root / "package" / "service.py"
            module.parent.mkdir()
            module.write_text("from . import helpers\nfrom ..core import settings\n", encoding="utf-8")
            info = extract_python_file(module, project_root=root)
            self.assertEqual(info.imports, [".helpers", "..core.settings"])


if __name__ == "__main__":
    unittest.main()
