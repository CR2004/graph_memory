from fastapi.testclient import TestClient

SAMPLE = {"description": "Lunch", "amount": 12.5, "spent_on": "2026-06-22"}


def test_create_expense(client: TestClient) -> None:
    resp = client.post("/expenses", json=SAMPLE)
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["description"] == "Lunch"
    assert body["amount"] == 12.5


def test_create_rejects_invalid_amount(client: TestClient) -> None:
    resp = client.post("/expenses", json={**SAMPLE, "amount": -5})
    assert resp.status_code == 422


def test_list_expenses(client: TestClient) -> None:
    client.post("/expenses", json=SAMPLE)
    client.post("/expenses", json={**SAMPLE, "description": "Coffee", "amount": 3})
    resp = client.get("/expenses")
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_list_empty(client: TestClient) -> None:
    assert client.get("/expenses").json() == []


def test_delete_expense(client: TestClient) -> None:
    created = client.post("/expenses", json=SAMPLE).json()
    resp = client.delete(f"/expenses/{created['id']}")
    assert resp.status_code == 204
    assert client.get("/expenses").json() == []


def test_delete_missing_returns_404(client: TestClient) -> None:
    resp = client.delete("/expenses/999")
    assert resp.status_code == 404
