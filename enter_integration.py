"""Core operations exposed to Enter Code through the local MCP server."""

from __future__ import annotations

import os
from pathlib import Path
import json
import re
from typing import Any

from ast_extractor import extract_python_file
from graph_store import GraphStore
from graph_visualizer import export_interactive_html
from memory_client import ParcleMemory
from token_utils import (
    compare_token_costs,
    count_tokens,
    python_source_files,
    repository_text,
)


WORKSPACE_ROOT = Path(__file__).resolve().parent


def _configured_project_root() -> Path:
    configured = Path(os.getenv("ARCH_MEMORY_PROJECT_ROOT", "vibe_workspace"))
    root = configured.resolve() if configured.is_absolute() else (WORKSPACE_ROOT / configured).resolve()
    try:
        root.relative_to(WORKSPACE_ROOT)
    except ValueError as exc:
        raise ValueError("ARCH_MEMORY_PROJECT_ROOT must stay inside this workspace") from exc
    root.mkdir(parents=True, exist_ok=True)
    return root


PROJECT_ROOT = _configured_project_root()


def contribution_mode() -> str:
    """Return the experimental condition while keeping Parcle active."""

    mode = os.getenv("ARCH_MEMORY_MODE", "architectural")
    if mode not in {"architectural", "raw_parcle"}:
        raise ValueError("ARCH_MEMORY_MODE must be 'architectural' or 'raw_parcle'")
    return mode


def parcle_project_id() -> str:
    """Return the remote Parcle namespace for the active comparison run."""

    return os.getenv("PARCLE_PROJECT_ID", PROJECT_ROOT.name)


def check_architectural_memory(request: str) -> dict[str, Any]:
    """Ask Parcle whether the requested capability already exists."""

    mode = contribution_mode()
    memory = ParcleMemory(project_id=parcle_project_id())
    result = memory.query(request)
    tokens = compare_token_costs(
        label="Enter Code preflight",
        project_root=PROJECT_ROOT,
        question=request,
        memory_result=result,
        cumulative_saved=0,
    )
    token_cost = {
        "full_repo": tokens.without_memory,
        "parcle_exchange": tokens.with_memory,
        "difference": tokens.saved,
        "difference_percent": round(tokens.saved_percent, 1),
    }
    return {
        **result,
        "contribution_mode": mode,
        "token_cost": token_cost,
        "instruction": (
            "Prefer extending the cited module instead of generating a duplicate."
            if result["match_found"]
            else "No prior decision matched; generation may proceed."
        ),
    }


def _current_graph() -> GraphStore:
    graph = GraphStore(PROJECT_ROOT)
    for path in python_source_files(PROJECT_ROOT):
        graph.add_or_update_node(extract_python_file(path, project_root=PROJECT_ROOT))
    return graph


def plan_architectural_change(
    request: str,
    max_targets: int = 3,
    max_initial_files: int = 3,
    max_source_tokens: int = 1500,
) -> dict[str, Any]:
    """Return a prompt-first, token-budgeted architectural change packet."""

    if contribution_mode() != "architectural":
        raise ValueError(
            "plan_architectural_change is treatment-only; use "
            "check_architectural_memory in raw_parcle mode"
        )
    memory_result = ParcleMemory(project_id=parcle_project_id()).query(request)
    graph = _current_graph()
    answer = str(memory_result.get("answer", ""))
    first_section = re.split(r"\n\s*\n|```|^###", answer, maxsplit=1)[0]
    decision_excerpt = " ".join(first_section.split())[:320]
    lowered_answer = answer.lower().replace("`", "")
    module_hints = sorted(
        str(module)
        for module in graph.graph.nodes
        if str(module).lower() in lowered_answer
        or Path(str(module)).name.lower() in lowered_answer
    )
    compact_memory = {
        "match_found": bool(memory_result.get("match_found")),
        "confidence": float(memory_result.get("confidence", 0.0)),
        "decision_excerpt": decision_excerpt,
        "module_hints": module_hints,
        "citations": memory_result.get("citations", []),
    }

    all_limit = max(1, graph.graph.number_of_nodes())
    prompt_ranked = graph.rank_nodes(request, limit=all_limit)
    semantic_ranked = {
        item["module"]: item
        for item in graph.rank_nodes(decision_excerpt, limit=all_limit)
    }
    ranked_by_module = {item["module"]: dict(item) for item in prompt_ranked}
    for module in module_hints:
        ranked_by_module.setdefault(
            module,
            {
                "module": module,
                "score": 0,
                "matched_terms": [],
                "module_matches": [],
                "symbol_matches": [],
                "doc_matches": [],
            },
        )
    tests_requested = bool(re.search(r"\btests?\b", request, flags=re.IGNORECASE))
    ranked: list[dict[str, Any]] = []
    for module, item in ranked_by_module.items():
        semantic_score = float(semantic_ranked.get(module, {}).get("score", 0))
        score = float(item["score"]) * 3 + min(semantic_score, 8) * 0.5
        if module in module_hints:
            score += 2
        if str(module).startswith("tests/") and not tests_requested:
            score *= 0.5
        item["score"] = round(score, 1)
        item["memory_hint"] = module in module_hints
        ranked.append(item)
    ranked.sort(key=lambda item: (-item["score"], item["module"]))
    targets = ranked[: max(1, max_targets)]

    generic_terms = {
        "expense", "route", "service", "storage", "create", "list", "delete",
    }
    distinctive_terms = graph._keywords(request) - generic_terms
    evidence = []
    evidence_counts: dict[str, int] = {}
    for item in ranked:
        if str(item["module"]).startswith("tests/"):
            continue
        terms = sorted(set(item.get("symbol_matches", [])) & distinctive_terms)
        if terms:
            evidence.append({"module": item["module"], "matched_symbols": terms})
            for term in terms:
                evidence_counts[term] = evidence_counts.get(term, 0) + 1
    likely_exists = any(count >= 2 for count in evidence_counts.values())
    capability = {
        "status": "likely_exists" if likely_exists else "change_needed_or_uncertain",
        "evidence": evidence[:5],
    }

    file_limit = min(max(1, max_initial_files), 2 if likely_exists else max_initial_files)
    initial_reads = []
    selected: list[str] = []
    selected_source_tokens = 0
    for target in targets:
        module = str(target["module"])
        path = PROJECT_ROOT / module
        if not path.is_file():
            continue
        source_tokens = count_tokens(f"# {module}\n{path.read_text(encoding='utf-8')}")
        if selected and selected_source_tokens + source_tokens > max_source_tokens:
            continue
        selected.append(module)
        selected_source_tokens += source_tokens
        initial_reads.append({"module": module, "source_tokens": source_tokens})
        if len(selected) >= file_limit:
            break

    neighbor_hints = []
    seen_hints: set[tuple[str, str, str]] = set()
    for module in selected:
        for neighbor in sorted(graph.graph.successors(module)):
            hint = (module, str(neighbor), "dependency")
            if neighbor not in selected and hint not in seen_hints:
                seen_hints.add(hint)
                neighbor_hints.append(
                    {"target": module, "module": neighbor, "relation": "imports"}
                )
            if len(neighbor_hints) >= 6:
                break
        if len(neighbor_hints) >= 6:
            break
        for neighbor in sorted(graph.graph.predecessors(module)):
            hint = (module, str(neighbor), "dependent")
            if neighbor not in selected and hint not in seen_hints:
                seen_hints.add(hint)
                neighbor_hints.append(
                    {"target": module, "module": neighbor, "relation": "imported_by"}
                )
            if len(neighbor_hints) >= 6:
                break
        if len(neighbor_hints) >= 6:
            break

    public_targets = [
        {
            "module": item["module"],
            "score": item["score"],
            "matched_terms": item["matched_terms"],
            "memory_hint": item["memory_hint"],
        }
        for item in targets
    ]

    change_packet = {
        "capability": capability,
        "likely_change_targets": public_targets,
        "recommended_reads": selected,
        "initial_reads": initial_reads,
        "neighbor_hints": neighbor_hints,
        "expansion_policy": (
            "Neighbors are metadata only. Read one additional file only for an "
            "unresolved symbol, contract, or failing test."
        ),
    }
    focused_payload = {
        "request": request,
        "memory": compact_memory,
        "change_packet": change_packet,
    }
    full_repo_tokens = count_tokens(f"{request}\n{repository_text(PROJECT_ROOT)}")
    packet_tokens = count_tokens(json.dumps(focused_payload, sort_keys=True))
    focused_total = packet_tokens + selected_source_tokens
    saved = full_repo_tokens - focused_total
    return {
        "contribution_mode": "architectural",
        "memory": compact_memory,
        "change_packet": change_packet,
        "token_cost": {
            "full_repository": full_repo_tokens,
            "focused_change_packet": packet_tokens,
            "recommended_source": selected_source_tokens,
            "focused_total": focused_total,
            "difference": saved,
            "difference_percent": round(
                (saved / full_repo_tokens * 100) if full_repo_tokens else 0.0, 1
            ),
        },
        "instruction": (
            "Verify the existing capability before editing. Read only recommended_reads."
            if likely_exists
            else "Read only recommended_reads. Treat neighbors as hints and expand one file at a time."
        ),
    }
def _resolve_changed_file(file_name: str) -> Path:
    candidate = Path(file_name)
    path = candidate.resolve() if candidate.is_absolute() else (PROJECT_ROOT / candidate).resolve()
    try:
        path.relative_to(PROJECT_ROOT.resolve())
    except ValueError as exc:
        raise ValueError(f"Changed file must be inside {PROJECT_ROOT}") from exc
    if path.suffix != ".py" or not path.is_file():
        raise ValueError(f"Changed file must be an existing Python file: {file_name}")
    return path


def sync_architectural_changes(
    changed_files: list[str],
    prompt_description: str,
    decision: str,
    rationale: str,
    session_id: str | None = None,
    deleted_files: list[str] | None = None,
) -> dict[str, Any]:
    """Rebuild structural facts and persist the decision after Enter edits code."""

    resolved_changes = [_resolve_changed_file(file_name) for file_name in changed_files]
    deleted_files = deleted_files or []
    for file_name in deleted_files:
        path = (PROJECT_ROOT / file_name).resolve()
        try:
            path.relative_to(PROJECT_ROOT.resolve())
        except ValueError as exc:
            raise ValueError(f"Deleted file must be inside {PROJECT_ROOT}") from exc
        if path.suffix != ".py" or path.exists():
            raise ValueError(f"Expected a deleted Python file: {file_name}")
    graph = _current_graph()

    named_json = WORKSPACE_ROOT / f"graph_{PROJECT_ROOT.name}.json"
    named_visual = WORKSPACE_ROOT / f"graph_{PROJECT_ROOT.name}.html"
    graph.export_json(named_json)
    export_interactive_html(graph.to_node_link_data(), named_visual)
    # Keep convenient aliases pointing at the most recently synchronized project.
    graph.export_json(WORKSPACE_ROOT / "graph.json")
    export_interactive_html(graph.to_node_link_data(), WORKSPACE_ROOT / "graph_visual.html")

    mode = contribution_mode()
    memory = ParcleMemory(project_id=parcle_project_id())
    active_session = session_id
    recorded: list[dict[str, str]] = []
    modules = [path.relative_to(PROJECT_ROOT).as_posix() for path in resolved_changes]
    if mode == "raw_parcle":
        active_session = memory.record_raw_event(
            prompt_description=prompt_description,
            assistant_summary=f"Implemented the request. Changed files: {', '.join([*modules, *deleted_files])}.",
            session_id=active_session,
        )
        recorded.append({"event": "raw_prompt", "session_id": active_session})
    else:
        for module in modules:
            active_session = memory.record_decision(
                module=module,
                prompt_description=prompt_description,
                decision=decision,
                rationale=rationale,
                session_id=active_session,
            )
            recorded.append({"module": module, "session_id": active_session})
        for module in deleted_files:
            active_session = memory.record_decision(
                module=module,
                prompt_description=prompt_description,
                decision=f"Deleted {module}. {decision}",
                rationale=rationale,
                session_id=active_session,
            )
            recorded.append({"module": module, "session_id": active_session})

    return {
        "contribution_mode": mode,
        "recorded": recorded,
        "graph": {
            "nodes": graph.graph.number_of_nodes(),
            "edges": graph.graph.number_of_edges(),
            "dependencies": [
                {"source": source, "target": target}
                for source, target in sorted(graph.graph.edges)
            ],
            "json": str(named_json),
            "visual": str(named_visual),
        },
    }


def get_architecture_graph() -> dict[str, Any]:
    """Return the latest compact graph summary for Enter's planning context."""

    graph = _current_graph()
    return {
        "project_root": str(PROJECT_ROOT),
        "modules": sorted(graph.graph.nodes),
        "dependencies": [
            {"source": source, "target": target}
            for source, target in sorted(graph.graph.edges)
        ],
    }
