import pytest
from fastapi.testclient import TestClient

from app import config, database, main


@pytest.fixture()
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "test.db"
    monkeypatch.setattr(database, "DB_PATH", db_path)
    monkeypatch.setattr(config, "MONTHLY_LIMIT", 10.0)
    database.init_db(db_path)
    with TestClient(main.create_app()) as c:
        yield c


def _add(client, amount):
    return client.post(
        "/expenses",
        json={"description": "x", "amount": amount, "category": "food"},
    )


def test_alert_under_limit(client):
    _add(client, 4.0)
    body = client.get("/budget/alert").json()
    assert body["limit"] == 10.0
    assert body["spent"] == 4.0
    assert body["remaining"] == 6.0
    assert body["over_limit"] is False


def test_alert_over_limit(client):
    _add(client, 7.0)
    _add(client, 5.0)
    body = client.get("/budget/alert").json()
    assert body["spent"] == 12.0
    assert body["remaining"] == -2.0
    assert body["over_limit"] is True


def test_alert_other_month_excluded(client):
    _add(client, 9.0)
    body = client.get("/budget/alert", params={"month": "1999-01"}).json()
    assert body["month"] == "1999-01"
    assert body["spent"] == 0.0
    assert body["over_limit"] is False
