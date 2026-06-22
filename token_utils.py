"""Replaceable token-cost instrumentation for memory-vs-repository reads."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import tiktoken


EXCLUDED_SOURCE_DIRECTORIES = {
    ".git",
    ".pytest_cache",
    ".venv",
    "__pycache__",
    "env",
    "venv",
}


def python_source_files(project_root: str | Path) -> list[Path]:
    """Return project Python files while excluding environments and caches."""

    root = Path(project_root)
    return sorted(
        path
        for path in root.rglob("*.py")
        if not any(part in EXCLUDED_SOURCE_DIRECTORIES for part in path.relative_to(root).parts)
    )



TOKEN_COUNTER_NAME = "tiktoken (cl100k_base)" 


def count_tokens(text: str) -> int:
    """Count tokens accurately when tiktoken exists, otherwise estimate by words."""

    if tiktoken:
        return len(tiktoken.get_encoding("cl100k_base").encode(text))
    return len(text.split())


def repository_text(project_root: str | Path) -> str:
    """Return the full Python context used by the no-memory baseline."""

    root = Path(project_root)
    sections: list[str] = []
    for path in python_source_files(root):
        sections.append(f"# {path.relative_to(root).as_posix()}\n{path.read_text(encoding='utf-8')}")
    return "\n\n".join(sections)


@dataclass(frozen=True, slots=True)
class TokenComparison:
    label: str
    without_memory: int
    with_memory: int
    saved: int
    saved_percent: float
    cumulative_saved: int


def compare_token_costs(
    *,
    label: str,
    project_root: str | Path,
    question: str,
    memory_result: dict[str, object],
    cumulative_saved: int,
) -> TokenComparison:
    without = count_tokens(repository_text(project_root))
    memory_payload = "\n".join(
        [
            question,
            str(memory_result.get("answer", "")),
            json.dumps(memory_result.get("citations", []), sort_keys=True),
        ]
    )
    with_memory = count_tokens(memory_payload)
    saved = without - with_memory
    percent = (saved / without * 100) if without else 0.0
    return TokenComparison(
        label=label,
        without_memory=without,
        with_memory=with_memory,
        saved=saved,
        saved_percent=percent,
        cumulative_saved=cumulative_saved + saved,
    )
