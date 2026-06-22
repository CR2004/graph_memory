"""A small, persistent-friendly architectural graph built on NetworkX."""

from __future__ import annotations

import json
import re
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

import networkx as nx
from networkx.readwrite import json_graph

from ast_extractor import ModuleInfo


class GraphStore:
    """Store modules as nodes and local imports as directed edges."""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root).resolve()
        self.graph = nx.DiGraph()

    def add_or_update_node(self, info: ModuleInfo | dict[str, Any]) -> None:
        data = info.to_dict() if isinstance(info, ModuleInfo) else dict(info)
        module = str(data.pop("module"))
        self.graph.add_node(module, **data)
        self._rebuild_local_import_edges()

    @staticmethod
    def _dotted_module(module_path: str) -> str:
        path = PurePosixPath(module_path)
        if path.name == "__init__.py":
            return ".".join(path.parent.parts)
        return ".".join(path.with_suffix("").parts)

    def _resolve_import(self, importer: str, imported: str) -> str | None:
        candidates = {
            self._dotted_module(node): node
            for node in self.graph.nodes
            if str(node).endswith(".py")
        }
        importer_package = self._dotted_module(importer).split(".")[:-1]

        if imported.startswith("."):
            level = len(imported) - len(imported.lstrip("."))
            tail = imported[level:]
            keep = max(0, len(importer_package) - level + 1)
            absolute = ".".join([*importer_package[:keep], tail]).strip(".")
        else:
            absolute = imported

        # ``from package.module import symbol`` may include a non-module tail.
        parts = absolute.split(".")
        for end in range(len(parts), 0, -1):
            candidate = ".".join(parts[:end])
            if candidate in candidates:
                return candidates[candidate]
        return None

    def _rebuild_local_import_edges(self) -> None:
        self.graph.remove_edges_from(list(self.graph.edges))
        for importer, attributes in list(self.graph.nodes(data=True)):
            for imported in attributes.get("imports", []):
                target = self._resolve_import(str(importer), str(imported))
                if target and target != importer:
                    self.graph.add_edge(importer, target, relationship="imports")

    @staticmethod
    def _keywords(*values: str) -> set[str]:
        """Normalize architectural vocabulary for deterministic intent matching."""

        words = set(re.findall(r"[a-z]+", " ".join(values).lower().replace("_", " ")))
        aliases = {
            "expenses": "expense",
            "spending": "expense",
            "budgets": "budget",
            "limit": "budget",
            "limits": "budget",
            "threshold": "budget",
            "thresholds": "budget",
            "alerts": "alert",
            "warn": "alert",
            "warning": "alert",
            "warnings": "alert",
            "aggregate": "summary",
            "aggregation": "summary",
            "summaries": "summary",
            "summarize": "summary",
            "summarized": "summary",
            "summarizing": "summary",
            "total": "summary",
            "totals": "summary",
            "api": "route",
            "endpoint": "route",
            "endpoints": "route",
            "router": "route",
            "routes": "route",
            "crud": "storage",
            "data": "storage",
            "database": "storage",
            "db": "storage",
            "repository": "storage",
            "repositories": "storage",
            "calculation": "service",
            "calculations": "service",
            "logic": "service",
            "services": "service",
            "categories": "category",
            "monthly": "month",
            "months": "month",
        }
        normalized = {aliases.get(word, word) for word in words}
        return normalized - {
            "a", "add", "an", "and", "app", "as", "by", "for", "from", "get",
            "in", "is", "it", "new", "of", "on", "or", "py", "return",
            "returns", "set", "test", "tests", "the", "to", "with",
        }

    def rank_nodes(self, intent: str, *, limit: int = 3) -> list[dict[str, Any]]:
        """Rank modules against semantic intent using AST names and docstrings."""

        intent_words = self._keywords(intent)
        lowered_intent = intent.lower().replace("`", "")
        ranked: list[dict[str, Any]] = []
        for module, attrs in self.graph.nodes(data=True):
            module_words = self._keywords(str(module))
            symbol_words = self._keywords(
                *attrs.get("functions", []), *attrs.get("classes", [])
            )
            doc_words = self._keywords(str(attrs.get("docstring") or ""))
            module_matches = intent_words & module_words
            symbol_matches = intent_words & symbol_words
            doc_matches = intent_words & doc_words
            score = (
                4 * len(module_matches)
                + 3 * len(symbol_matches)
                + len(doc_matches)
            )
            if str(module).lower() in lowered_intent:
                score += 10
            if score:
                ranked.append(
                    {
                        "module": module,
                        "score": score,
                        "matched_terms": sorted(
                            module_matches | symbol_matches | doc_matches
                        ),
                        "module_matches": sorted(module_matches),
                        "symbol_matches": sorted(symbol_matches),
                        "doc_matches": sorted(doc_matches),
                    }
                )
        return sorted(ranked, key=lambda item: (-item["score"], item["module"]))[:limit]

    def similar_nodes(self, module: str, *, limit: int = 5) -> list[dict[str, Any]]:
        """Rank nodes by shared identifier keywords (a semantic placeholder)."""

        if module not in self.graph:
            return []

        def keywords(node: str) -> set[str]:
            attrs = self.graph.nodes[node]
            values: Iterable[str] = [
                node,
                *attrs.get("functions", []),
                *attrs.get("classes", []),
            ]
            normalized = self._keywords(*values)
            raw_words = set(
                re.findall(r"[a-z]+", " ".join(values).lower().replace("_", " "))
            )
            if raw_words & {"limit", "limited", "limiter", "rate", "throttle", "throttling"}:
                normalized.add("throttling")
            return normalized

        source_words = keywords(module)
        matches: list[dict[str, Any]] = []
        for candidate in self.graph.nodes:
            if candidate == module:
                continue
            shared = sorted(source_words & keywords(str(candidate)))
            if shared:
                matches.append({"module": candidate, "shared_keywords": shared, "score": len(shared)})
        return sorted(matches, key=lambda item: (-item["score"], item["module"]))[:limit]

    def to_node_link_data(self) -> dict[str, Any]:
        return json_graph.node_link_data(self.graph, edges="links")

    def export_json(self, destination: str | Path) -> Path:
        path = Path(destination)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_node_link_data(), indent=2), encoding="utf-8")
        return path
