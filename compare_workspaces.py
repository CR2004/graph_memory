"""Compare architectural-memory treatment with raw-Parcle control."""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from ast_extractor import extract_python_file
from graph_store import GraphStore
from memory_client import ParcleMemory
from token_utils import count_tokens, python_source_files, repository_text


ROOT = Path(__file__).resolve().parent


@dataclass(frozen=True, slots=True)
class ProjectMetrics:
    project: str
    python_files: int
    lines_of_code: int
    modules: int
    dependency_edges: int
    functions: int
    classes: int
    full_context_tokens: int


@dataclass(frozen=True, slots=True)
class PromptUsage:
    prompt_number: int
    prompt: str
    model_calls: int
    model_input_tokens: int
    output_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class EnterUsage:
    """Provider-reported token usage from one persisted Enter session."""

    session_id: str
    session_file: str
    user_prompts: int
    model_calls: int
    input_tokens: int
    cache_creation_input_tokens: int
    cache_read_input_tokens: int
    model_input_tokens: int
    output_tokens: int
    total_tokens: int
    prompt_usage: list[PromptUsage]


def analyze_project(project_root: Path) -> ProjectMetrics:
    """Measure code and structural graph size for one project."""

    graph = GraphStore(project_root)
    files = python_source_files(project_root)
    lines = 0
    function_count = 0
    class_count = 0
    for path in files:
        info = extract_python_file(path, project_root=project_root)
        graph.add_or_update_node(info)
        lines += len(path.read_text(encoding="utf-8").splitlines())
        function_count += len(info.functions)
        class_count += len(info.classes)
    return ProjectMetrics(
        project=project_root.name,
        python_files=len(files),
        lines_of_code=lines,
        modules=graph.graph.number_of_nodes(),
        dependency_edges=graph.graph.number_of_edges(),
        functions=function_count,
        classes=class_count,
        full_context_tokens=count_tokens(repository_text(project_root)),
    )


def enter_sessions_directory(project_root: Path) -> Path:
    """Return Enter's persisted-session directory for a project path."""

    encoded_project = str(project_root.resolve()).replace("/", "-")
    return Path.home() / ".enter" / "projects" / encoded_project / "sessions"


def find_enter_session(project_root: Path, session_id: str | None = None) -> Path | None:
    """Find an explicit session or the most recently modified project session."""

    sessions = enter_sessions_directory(project_root)
    if session_id:
        candidate = Path(session_id).expanduser()
        if candidate.is_file():
            return candidate
        candidate = sessions / f"{candidate.stem}.jsonl"
        if not candidate.is_file():
            raise FileNotFoundError(f"Enter session not found: {candidate}")
        return candidate
    python_files = python_source_files(project_root)
    if not python_files:
        return None
    latest_project_change = max(path.stat().st_mtime for path in python_files)
    candidates = [
        path for path in sessions.glob("*.jsonl")
        if path.stat().st_mtime >= latest_project_change
    ]
    return max(candidates, key=lambda path: path.stat().st_mtime) if candidates else None


def _user_prompt_text(record: dict[str, Any]) -> str | None:
    """Extract a real prompt while excluding tool results and injected reminders."""

    if record.get("role") != "user":
        return None
    content = record.get("content", "")
    if isinstance(content, str):
        text = content.strip()
        return text if text and not text.startswith("<system-reminder>") else None
    if not isinstance(content, list) or any(item.get("type") == "tool_result" for item in content):
        return None
    texts = [
        str(item.get("text", "")).strip()
        for item in content
        if item.get("type") == "text"
        and not str(item.get("text", "")).lstrip().startswith("<system-reminder>")
        and not str(item.get("text", "")).lstrip().startswith("<local-command>")
    ]
    return "\n".join(text for text in texts if text) or None


def analyze_enter_session(session_file: Path) -> EnterUsage:
    """Sum exact usage fields emitted by the model provider for one Enter session."""

    records: list[dict[str, Any]] = []
    for line in session_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            records.append(json.loads(line))
    usages = [record["usage"] for record in records if isinstance(record.get("usage"), dict)]

    prompt_buckets: list[dict[str, Any]] = []
    current_bucket: dict[str, Any] | None = None
    for record in records:
        prompt_text = _user_prompt_text(record)
        if prompt_text is not None:
            current_bucket = {"prompt": prompt_text, "usages": []}
            prompt_buckets.append(current_bucket)
        usage = record.get("usage")
        if current_bucket is not None and isinstance(usage, dict):
            current_bucket["usages"].append(usage)

    def total(field: str) -> int:
        return sum(int(usage.get(field, 0) or 0) for usage in usages)

    input_tokens = total("input_tokens")
    cache_creation = total("cache_creation_input_tokens")
    cache_read = total("cache_read_input_tokens")
    output_tokens = total("output_tokens")
    model_input = input_tokens + cache_creation + cache_read
    prompt_usage: list[PromptUsage] = []
    for number, bucket in enumerate(prompt_buckets, start=1):
        bucket_usages = bucket["usages"]

        def bucket_total(field: str) -> int:
            return sum(int(usage.get(field, 0) or 0) for usage in bucket_usages)

        bucket_input = (
            bucket_total("input_tokens")
            + bucket_total("cache_creation_input_tokens")
            + bucket_total("cache_read_input_tokens")
        )
        bucket_output = bucket_total("output_tokens")
        prompt_usage.append(
            PromptUsage(
                prompt_number=number,
                prompt=bucket["prompt"],
                model_calls=len(bucket_usages),
                model_input_tokens=bucket_input,
                output_tokens=bucket_output,
                total_tokens=bucket_input + bucket_output,
            )
        )
    return EnterUsage(
        session_id=session_file.stem,
        session_file=str(session_file),
        user_prompts=len(prompt_buckets),
        model_calls=len(usages),
        input_tokens=input_tokens,
        cache_creation_input_tokens=cache_creation,
        cache_read_input_tokens=cache_read,
        model_input_tokens=model_input,
        output_tokens=output_tokens,
        total_tokens=model_input + output_tokens,
        prompt_usage=prompt_usage,
    )


def compare(
    treatment_project: Path,
    control_project: Path,
    prompt: str | None = None,
    treatment_project_id: str = "vibe_contribution_on_20260621",
    control_project_id: str = "vibe_contribution_off_20260621",
    treatment_session_id: str | None = None,
    control_session_id: str | None = None,
) -> dict[str, Any]:
    """Return project metrics and optional live Parcle context comparison."""

    result: dict[str, Any] = {
        "contribution_on": asdict(analyze_project(treatment_project)),
        "raw_parcle_control": asdict(analyze_project(control_project)),
    }
    treatment_session = find_enter_session(treatment_project, treatment_session_id)
    control_session = find_enter_session(control_project, control_session_id)
    if treatment_session and control_session:
        result["enter_usage"] = {
            "contribution_on": asdict(analyze_enter_session(treatment_session)),
            "raw_parcle_control": asdict(analyze_enter_session(control_session)),
        }
    if prompt:
        treatment_result = ParcleMemory(project_id=treatment_project_id).query(prompt)
        control_result = ParcleMemory(project_id=control_project_id).query(prompt)

        def exchange_tokens(memory_result: dict[str, Any]) -> int:
            payload = "\n".join(
                [prompt, memory_result["answer"], json.dumps(memory_result["citations"])]
            )
            return count_tokens(payload)

        treatment_tokens = exchange_tokens(treatment_result)
        control_tokens = exchange_tokens(control_result)
        result["prompt_comparison"] = {
            "prompt": prompt,
            "contribution_on": {
                "answer": treatment_result["answer"],
                "confidence": treatment_result["confidence"],
                "citations": treatment_result["citations"],
                "parcle_exchange_tokens": treatment_tokens,
            },
            "raw_parcle_control": {
                "answer": control_result["answer"],
                "confidence": control_result["confidence"],
                "citations": control_result["citations"],
                "parcle_exchange_tokens": control_tokens,
            },
            "token_difference": control_tokens - treatment_tokens,
        }
    return result


def print_report(result: dict[str, Any]) -> None:
    columns = (result["contribution_on"], result["raw_parcle_control"])
    print("\nPROJECT COMPARISON")
    print("=" * 70)
    print(f"{'Metric':<26}{'Contribution ON':>18}{'Raw Parcle':>18}")
    print("-" * 70)
    labels = {
        "python_files": "Python files",
        "lines_of_code": "Lines of code",
        "modules": "Graph modules",
        "dependency_edges": "Dependency edges",
        "functions": "Functions",
        "classes": "Classes",
        "full_context_tokens": "Full-context tokens",
    }
    for key, label in labels.items():
        print(f"{label:<26}{columns[0][key]:>18,}{columns[1][key]:>18,}")
    if "enter_usage" in result:
        usage = result["enter_usage"]
        treatment = usage["contribution_on"]
        control = usage["raw_parcle_control"]
        print("\nENTER PROVIDER TOKEN USAGE")
        print(f"  {'Metric':<28}{'Contribution ON':>18}{'Raw Parcle':>18}")
        usage_labels = {
            "user_prompts": "User prompts",
            "model_calls": "Model calls",
            "input_tokens": "Uncached input tokens",
            "cache_creation_input_tokens": "Cache creation tokens",
            "cache_read_input_tokens": "Cache read tokens",
            "model_input_tokens": "Total model input",
            "output_tokens": "Output tokens",
            "total_tokens": "Total provider tokens",
        }
        for key, label in usage_labels.items():
            print(f"  {label:<28}{treatment[key]:>18,}{control[key]:>18,}")
        print(f"  Sessions: {treatment['session_id']} / {control['session_id']}")
        if treatment["user_prompts"] != control["user_prompts"]:
            print("  WARNING: session prompt counts differ; totals are not directly comparable.")
        else:
            print("\nPER-PROMPT TOKEN GROWTH")
            print(
                f"  {'Prompt':<10}{'Contribution ON':>18}{'Raw Parcle':>18}"
                f"{'Raw - ON':>14}{'Cumulative ON':>18}{'Cumulative Raw':>18}"
            )
            cumulative_treatment = 0
            cumulative_control = 0
            for treatment_prompt, control_prompt in zip(
                treatment["prompt_usage"], control["prompt_usage"], strict=True
            ):
                cumulative_treatment += treatment_prompt["total_tokens"]
                cumulative_control += control_prompt["total_tokens"]
                difference = control_prompt["total_tokens"] - treatment_prompt["total_tokens"]
                print(
                    f"  {treatment_prompt['prompt_number']:<10}"
                    f"{treatment_prompt['total_tokens']:>18,}"
                    f"{control_prompt['total_tokens']:>18,}"
                    f"{difference:>14,}"
                    f"{cumulative_treatment:>18,}"
                    f"{cumulative_control:>18,}"
                )
    if "prompt_comparison" in result:
        prompt = result["prompt_comparison"]
        print("\nPROMPT CONTEXT COMPARISON")
        treatment = prompt["contribution_on"]
        control = prompt["raw_parcle_control"]
        print(f"  Contribution ON: {treatment['parcle_exchange_tokens']:,} tokens")
        print(f"  Raw Parcle:      {control['parcle_exchange_tokens']:,} tokens")
        print(f"  Token difference: {prompt['token_difference']:,}")
        print(f"  Contribution confidence: {treatment['confidence']:.0%}")
        print(f"  Control confidence:      {control['confidence']:.0%}")
        print(f"  Contribution citations: {treatment['citations'] or 'none'}")
        print(f"  Control citations:      {control['citations'] or 'none'}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two vibe-coded workspaces")
    parser.add_argument("--contribution-on", default="vibe_workspace")
    parser.add_argument("--raw-parcle", default="vibe_workspace_2")
    parser.add_argument(
        "--contribution-on-id",
        default=os.getenv("PARCLE_PROJECT_ID", "vibe_contribution_on_20260621"),
    )
    parser.add_argument("--raw-parcle-id", default="vibe_contribution_off_20260621")
    parser.add_argument(
        "--contribution-session",
        help="Enter session ID or JSONL path; defaults to the latest treatment session",
    )
    parser.add_argument(
        "--raw-parcle-session",
        help="Enter session ID or JSONL path; defaults to the latest control session",
    )
    parser.add_argument("--prompt", help="Run the same live query against both Parcle scopes")
    parser.add_argument("--json", action="store_true", help="Print JSON instead of a table")
    args = parser.parse_args()
    result = compare(
        ROOT / args.contribution_on,
        ROOT / args.raw_parcle,
        args.prompt,
        args.contribution_on_id,
        args.raw_parcle_id,
        args.contribution_session,
        args.raw_parcle_session,
    )
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_report(result)


if __name__ == "__main__":
    main()
