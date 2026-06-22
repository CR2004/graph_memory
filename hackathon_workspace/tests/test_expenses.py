import pytest
from fastapi.testclient import TestClient

from app import db
from app.main import app


@pytest.fixture
def client(tmp_path):
    db.configure(str(tmp_path / "test.db"))
    db.init_db()
    return TestClient(app)


def test_create_expense(client):
    resp = client.post("/expenses", json={"description": "Coffee", "amount": 4.5})
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"] == 1
    assert body["description"] == "Coffee"
    assert body["amount"] == 4.5


def test_list_expenses(client):
    client.post("/expenses", json={"description": "Lunch", "amount": 12.0})
    client.post("/expenses", json={"description": "Bus", "amount": 2.0})
    resp = client.get("/expenses")
    assert resp.status_code == 200
    assert [e["description"] for e in resp.json()] == ["Lunch", "Bus"]


def test_delete_expense(client):
    created = client.post("/expenses", json={"description": "Book", "amount": 9.0}).json()
    assert client.delete(f"/expenses/{created['id']}").status_code == 204
    assert client.get("/expenses").json() == []
    assert client.delete(f"/expenses/{created['id']}").status_code == 404
