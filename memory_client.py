"""Project-shaped wrapper around the real Parcle SDK."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from parcle.exceptions import NotFoundError


def _load_local_env() -> None:
    """Load a simple project-local .env file without another dependency."""

    env_path = Path(__file__).resolve().with_name(".env")
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_local_env()

DEFAULT_PROJECT_ID = os.getenv("PARCLE_PROJECT_ID", "vibe_workspace")


class ParcleMemory:
    """Translate architectural-memory operations into Parcle primitives."""

    def __init__(
        self,
        project_id: str = DEFAULT_PROJECT_ID,
        *,
        confidence_threshold: float = 0.5,
        client: Any | None = None,
    ) -> None:
        self.project_id = project_id
        self.confidence_threshold = confidence_threshold
        self._user_ready = False
        if client is not None:
            self.client = client
        else:
            try:
                from parcle import Parcle
            except ImportError as exc:
                raise RuntimeError(
                    "Real Parcle mode requires the 'parcle' package. Install requirements.txt first."
                ) from exc
            self.client = Parcle(api_key=os.getenv("PARCLE_API_KEY"))

    def _ensure_user(self) -> None:
        """Create the Parcle project namespace once before its first ingest."""

        if not self._user_ready:
            self.client.create_user(user_id=self.project_id, name=self.project_id)
            self._user_ready = True

    def record_decision(
        self,
        module: str,
        prompt_description: str,
        decision: str,
        rationale: str,
        session_id: str | None = None,
    ) -> str:
        self._ensure_user()
        messages = [
            {"role": "user", "content": prompt_description},
            {
                "role": "assistant",
                "content": f"Created {module}. Decision: {decision}. Rationale: {rationale}.",
            },
        ]
        kwargs: dict[str, Any] = {"user_id": self.project_id, "messages": messages}
        if session_id is not None:
            kwargs["session_id"] = session_id
        dialog = self.client.ingest_dialog(**kwargs)
        return str(dialog.session_id)

    def record_raw_event(
        self,
        prompt_description: str,
        assistant_summary: str,
        session_id: str | None = None,
    ) -> str:
        """Store an unstructured Parcle conversation for the control condition."""

        self._ensure_user()
        kwargs: dict[str, Any] = {
            "user_id": self.project_id,
            "messages": [
                {"role": "user", "content": prompt_description},
                {"role": "assistant", "content": assistant_summary},
            ],
        }
        if session_id is not None:
            kwargs["session_id"] = session_id
        dialog = self.client.ingest_dialog(**kwargs)
        return str(dialog.session_id)

    def query(self, question: str) -> dict[str, Any]:
        try:
            result = self.client.search(user_id=self.project_id, query=question)
        except NotFoundError as exc:
            if exc.code != "user_not_found":
                raise
            return {
                "match_found": False,
                "confidence": 0.0,
                "answer": "No architectural decisions have been recorded for this project yet.",
                "citations": [],
            }
        confidence = float(result.confidence)
        citations = [
            {
                "type": citation["type"] if isinstance(citation, dict) else citation.type,
                "id": citation["id"] if isinstance(citation, dict) else citation.id,
            }
            for citation in (result.citations or [])
        ]
        return {
            "match_found": confidence >= self.confidence_threshold,
            "confidence": confidence,
            "answer": str(result.answer),
            "citations": citations,
        }
