from fastapi.testclient import TestClient


def _add(client: TestClient, amount: float, category: str | None = None) -> None:
    payload = {"description": "x", "amount": amount, "spent_on": "2026-06-10"}
    if category is not None:
        payload["category"] = category
    assert client.post("/expenses", json=payload).status_code == 201


def test_summary_empty(client: TestClient) -> None:
    assert client.get("/expenses/summary").json() == []


def test_summary_groups_by_category(client: TestClient) -> None:
    _add(client, 12.5, "food")
    _add(client, 3.5, "food")
    _add(client, 2.0, "transport")
    resp = client.get("/expenses/summary")
    assert resp.status_code == 200
    assert resp.json() == [
        {"category": "food", "total": 16.0},
        {"category": "transport", "total": 2.0},
    ]


def test_summary_defaults_uncategorized(client: TestClient) -> None:
    _add(client, 5.0)
    assert client.get("/expenses/summary").json() == [
        {"category": "uncategorized", "total": 5.0},
    ]
