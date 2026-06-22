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


def _add(client, amount, category):
    return client.post(
        "/expenses",
        json={"description": "x", "amount": amount, "category": category},
    )


def test_summary_empty(client):
    assert client.get("/expenses/summary").json() == {}


def test_summary_groups_by_category(client):
    _add(client, 3.0, "food")
    _add(client, 2.5, "food")
    _add(client, 10.0, "transport")
    body = client.get("/expenses/summary").json()
    assert body == {"food": 5.5, "transport": 10.0}
