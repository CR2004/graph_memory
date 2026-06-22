"""Command-line fallback for Enter Code when custom MCP tools are unavailable."""

from __future__ import annotations

import argparse
import json
from typing import Any

from enter_integration import (
    PROJECT_ROOT,
    check_architectural_memory,
    get_architecture_graph,
    contribution_mode,
    parcle_project_id,
    plan_architectural_change,
    sync_architectural_changes,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Architectural memory operations")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check = subparsers.add_parser("check", help="Query Parcle before editing")
    check.add_argument("request")

    plan = subparsers.add_parser(
        "plan", help="Combine Parcle intent with a focused graph neighborhood"
    )
    plan.add_argument("request")
    plan.add_argument("--max-targets", type=int, default=3)
    plan.add_argument("--max-files", type=int, default=3)
    plan.add_argument("--max-source-tokens", type=int, default=1500)

    subparsers.add_parser("graph", help="Print current modules and dependencies")
    subparsers.add_parser("status", help="Print the active vibe-code project root")

    sync = subparsers.add_parser("sync", help="Record a decision and rebuild the graph")
    sync.add_argument("--changed", action="append", default=[])
    sync.add_argument("--deleted", action="append", default=[])
    sync.add_argument("--description", required=True)
    sync.add_argument("--decision", required=True)
    sync.add_argument("--rationale", required=True)
    sync.add_argument("--session-id")
    return parser


def execute(args: argparse.Namespace) -> dict[str, Any]:
    if args.command == "check":
        return check_architectural_memory(args.request)
    if args.command == "plan":
        return plan_architectural_change(
            args.request,
            max_targets=args.max_targets,
            max_initial_files=args.max_files,
            max_source_tokens=args.max_source_tokens,
        )
    if args.command == "graph":
        return get_architecture_graph()
    if args.command == "status":
        return {
            "project_root": str(PROJECT_ROOT),
            "project_id": parcle_project_id(),
            "contribution_mode": contribution_mode(),
        }
    if args.command == "sync":
        return sync_architectural_changes(
            changed_files=args.changed,
            prompt_description=args.description,
            decision=args.decision,
            rationale=args.rationale,
            session_id=args.session_id,
            deleted_files=args.deleted,
        )
    raise ValueError(f"Unsupported command: {args.command}")


def main() -> None:
    args = build_parser().parse_args()
    print(json.dumps(execute(args), indent=2))


if __name__ == "__main__":
    main()
