"""Static-analysis helpers for turning Python files into graph-ready records."""

from __future__ import annotations

import ast
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class ModuleInfo:
    """The architectural facts extracted from one Python module."""

    module: str
    functions: list[str]
    classes: list[str]
    imports: list[str]
    docstring: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _module_name(path: Path, project_root: Path | None) -> str:
    if project_root is None:
        return path.name
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(f"{path} is not inside project root {project_root}") from exc


def extract_python_file(
    file_path: str | Path, *, project_root: str | Path | None = None
) -> ModuleInfo:
    """Parse one Python file without executing it.

    Only top-level function and class definitions are included. Imports retain
    enough detail for :class:`graph_store.GraphStore` to resolve local modules.
    """

    path = Path(file_path)
    if path.suffix != ".py":
        raise ValueError(f"Expected a .py file, got: {path}")

    source = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError as exc:
        raise SyntaxError(f"Could not parse {path}: {exc.msg}") from exc

    functions: list[str] = []
    classes: list[str] = []
    imports: list[str] = []

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            prefix = "." * node.level
            base = f"{prefix}{node.module or ''}"
            imports.extend(
                (
                    f"{base}{alias.name}"
                    if base.endswith(".")
                    else f"{base}.{alias.name}"
                    if base
                    else alias.name
                )
                for alias in node.names
            )

    root = Path(project_root) if project_root is not None else None
    return ModuleInfo(
        module=_module_name(path, root),
        functions=functions,
        classes=classes,
        imports=imports,
        docstring=ast.get_docstring(tree, clean=True),
    )
