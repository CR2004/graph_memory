import pytest
from fastapi.testclient import TestClient

from app import database, main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    database.init_db(db_path)
    with TestClient(main.create_app()) as c:
        yield c


def _sample():
    return {"description": "Coffee", "amount": 3.5, "category": "food"}


def test_create_expense(client):
    resp = client.post("/expenses", json=_sample())
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] > 0
    assert body["description"] == "Coffee"
    assert body["amount"] == 3.5


def test_list_expenses(client):
    client.post("/expenses", json=_sample())
    client.post("/expenses", json={"description": "Bus", "amount": 2.0, "category": "transport"})
    resp = client.get("/expenses")
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) == 2
    assert {i["description"] for i in items} == {"Coffee", "Bus"}


def test_delete_expense(client):
    created = client.post("/expenses", json=_sample()).json()
    resp = client.delete(f"/expenses/{created['id']}")
    assert resp.status_code == 204
    assert client.get("/expenses").json() == []


def test_delete_missing_returns_404(client):
    resp = client.delete("/expenses/999")
    assert resp.status_code == 404


def test_create_validation_error(client):
    resp = client.post("/expenses", json={"description": "", "amount": -1, "category": ""})
    assert resp.status_code == 422
