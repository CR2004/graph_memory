from __future__ import annotations

import tempfile
import unittest

from graph_store import GraphStore


class GraphStoreTests(unittest.TestCase):
    def test_resolves_only_local_imports(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = GraphStore(directory)
            store.add_or_update_node({"module": "auth.py", "functions": [], "classes": [], "imports": ["middleware.throttle", "os"], "docstring": None})
            store.add_or_update_node({"module": "middleware/throttle.py", "functions": [], "classes": [], "imports": [], "docstring": None})
            self.assertIn(("auth.py", "middleware/throttle.py"), store.graph.edges)
            self.assertEqual(store.graph.number_of_edges(), 1)

    def test_similarity_normalizes_throttling_synonyms(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = GraphStore(directory)
            store.add_or_update_node({"module": "rate_limit.py", "functions": ["is_rate_limited"], "classes": [], "imports": [], "docstring": None})
            store.add_or_update_node({"module": "throttle.py", "functions": ["throttle_request"], "classes": [], "imports": [], "docstring": None})
            matches = store.similar_nodes("rate_limit.py")
            self.assertEqual(matches[0]["module"], "throttle.py")
            self.assertIn("throttling", matches[0]["shared_keywords"])

    def test_ranks_ast_modules_against_change_intent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            store = GraphStore(directory)
            store.add_or_update_node({
                "module": "app/routes.py",
                "functions": ["list_expenses"],
                "classes": [],
                "imports": ["app.services"],
                "docstring": "Expense API endpoints.",
            })
            store.add_or_update_node({
                "module": "app/services.py",
                "functions": ["summarize_spending_by_category"],
                "classes": [],
                "imports": [],
                "docstring": "Expense business logic.",
            })
            ranked = store.rank_nodes(
                "Add an endpoint returning total spending by category"
            )
            self.assertEqual(ranked[0]["module"], "app/services.py")
            self.assertIn("category", ranked[0]["matched_terms"])


if __name__ == "__main__":
    unittest.main()
