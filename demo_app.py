"""Local observer dashboard for Enter, Parcle, and the architecture graph."""

from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Any
from urllib.parse import urlparse

from ast_extractor import extract_python_file
from graph_store import GraphStore
from token_utils import python_source_files


ROOT = Path(__file__).resolve().parent
WEB_ROOT = ROOT / "demo"
LIVE_WORKSPACE = ROOT / "hackathon_workspace"
LIVE_PROJECT_ID = os.getenv(
    "HACKATHON_PARCLE_PROJECT_ID", "hackathon_demo_live_20260622"
)
SERVER_STARTED_AT = time.time()


def graph_payload(project_root: Path) -> dict[str, Any]:
    graph = GraphStore(project_root)
    source_files = python_source_files(project_root)
    for path in source_files:
        graph.add_or_update_node(extract_python_file(path, project_root=project_root))
    return {
        "project_root": str(project_root),
        "modules": sorted(graph.graph.nodes),
        "dependencies": [
            {"source": source, "target": target}
            for source, target in sorted(graph.graph.edges)
        ],
        "module_mtimes": {
            path.relative_to(project_root).as_posix(): path.stat().st_mtime
            for path in source_files
        },
    }


def _session_directory(project_root: Path) -> Path:
    encoded = str(project_root.resolve()).replace("/", "-")
    return Path.home() / ".enter" / "projects" / encoded / "sessions"


def usage_since(project_root: Path, started_at: float) -> dict[str, Any] | None:
    sessions = _session_directory(project_root)
    candidates = [
        path
        for path in sessions.glob("*.jsonl")
        if path.stat().st_mtime >= started_at - 1
    ]
    if not candidates:
        return None
    totals: dict[str, Any] = {
        "sessions": len(candidates),
        "model_calls": 0,
        "input_tokens": 0,
        "cache_creation_input_tokens": 0,
        "cache_read_input_tokens": 0,
        "output_tokens": 0,
    }
    for session in candidates:
        for line in session.read_text(encoding="utf-8").splitlines():
            try:
                usage = json.loads(line).get("usage")
            except json.JSONDecodeError:
                continue
            if not isinstance(usage, dict):
                continue
            totals["model_calls"] += 1
            for field_name in (
                "input_tokens",
                "cache_creation_input_tokens",
                "cache_read_input_tokens",
                "output_tokens",
            ):
                totals[field_name] += int(usage.get(field_name, 0) or 0)
    totals["model_input_tokens"] = (
        totals["input_tokens"]
        + totals["cache_creation_input_tokens"]
        + totals["cache_read_input_tokens"]
    )
    totals["total_tokens"] = totals["model_input_tokens"] + totals["output_tokens"]
    return totals


def enter_command() -> str:
    return (
        "cd hackathon_workspace && "
        "ARCH_MEMORY_PROJECT_ROOT=hackathon_workspace "
        f"PARCLE_PROJECT_ID={LIVE_PROJECT_ID} "
        "ARCH_MEMORY_MODE=architectural enter"
    )


def status_payload() -> dict[str, Any]:
    return {
        "project": LIVE_WORKSPACE.name,
        "mode": "architectural",
        "project_id": LIVE_PROJECT_ID,
        "enter_command": enter_command(),
        "graph": graph_payload(LIVE_WORKSPACE),
    }


def watch_payload() -> dict[str, Any]:
    return {
        "graph": graph_payload(LIVE_WORKSPACE),
        "usage": usage_since(LIVE_WORKSPACE, SERVER_STARTED_AT),
    }


def sample_payload() -> dict[str, Any]:
    payload = json.loads((WEB_ROOT / "sample_plan.json").read_text(encoding="utf-8"))
    payload["graph"] = json.loads(
        (WEB_ROOT / "sample_graph.json").read_text(encoding="utf-8")
    )
    return payload


def plan_live_workspace(request: str) -> dict[str, Any]:
    """Run only the Parcle + AST planner; this consumes no Enter credits."""

    env = os.environ.copy()
    env.update(
        {
            "ARCH_MEMORY_PROJECT_ROOT": LIVE_WORKSPACE.name,
            "PARCLE_PROJECT_ID": LIVE_PROJECT_ID,
            "ARCH_MEMORY_MODE": "architectural",
        }
    )
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "architecture_cli.py"),
            "plan",
            request,
        ],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        timeout=90,
        check=False,
    )
    if completed.returncode:
        message = completed.stderr.strip().splitlines()[-1] if completed.stderr.strip() else "Planner failed"
        raise RuntimeError(message)
    result = json.loads(completed.stdout)
    result["request"] = request
    result["graph"] = graph_payload(LIVE_WORKSPACE)
    return result


class DemoHandler(BaseHTTPRequestHandler):
    server_version = "ArchitecturalMemoryDemo/3.0"

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict[str, Any]:
        length = min(int(self.headers.get("Content-Length", "0")), 65_536)
        return json.loads(self.rfile.read(length) or b"{}")

    def _serve_static(self, relative: str) -> None:
        candidate = (WEB_ROOT / relative).resolve()
        try:
            candidate.relative_to(WEB_ROOT.resolve())
        except ValueError:
            self.send_error(404)
            return
        if not candidate.is_file():
            self.send_error(404)
            return
        body = candidate.read_bytes()
        content_type = mimetypes.guess_type(candidate.name)[0] or "application/octet-stream"
        self.send_response(200)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        path = urlparse(self.path).path
        if path == "/api/status":
            self._send_json(status_payload())
        elif path == "/api/watch":
            self._send_json(watch_payload())
        elif path == "/api/sample":
            self._send_json(sample_payload())
        elif path in {"/", "/index.html"}:
            self._serve_static("index.html")
        else:
            self._serve_static(path.lstrip("/"))

    def do_POST(self) -> None:  # noqa: N802
        if urlparse(self.path).path != "/api/plan":
            self.send_error(404)
            return
        try:
            request = str(self._read_json().get("request", "")).strip()
            if not request:
                self._send_json({"error": "A feature request is required."}, 400)
                return
            self._send_json(plan_live_workspace(request))
        except Exception as exc:
            self._send_json({"error": str(exc)}, 500)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[demo] {self.address_string()} {format % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the architectural-memory demo")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer(("127.0.0.1", args.port), DemoHandler)
    print(f"Architectural Memory demo: http://127.0.0.1:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
