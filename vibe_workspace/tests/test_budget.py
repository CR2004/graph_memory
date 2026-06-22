from fastapi.testclient import TestClient


def _add(client: TestClient, amount: float, spent_on: str) -> None:
    resp = client.post(
        "/expenses",
        json={"description": "x", "amount": amount, "spent_on": spent_on},
    )
    assert resp.status_code == 201


def test_set_monthly_limit(client: TestClient) -> None:
    resp = client.put("/budget/monthly-limit", json={"amount": 100})
    assert resp.status_code == 204


def test_alert_under_limit(client: TestClient) -> None:
    client.put("/budget/monthly-limit", json={"amount": 100})
    _add(client, 30, "2026-06-10")
    body = client.get("/budget/alert", params={"year": 2026, "month": 6}).json()
    assert body["spent"] == 30
    assert body["over_limit"] is False
    assert body["over_by"] == 0


def test_alert_over_limit(client: TestClient) -> None:
    client.put("/budget/monthly-limit", json={"amount": 50})
    _add(client, 40, "2026-06-10")
    _add(client, 25, "2026-06-15")
    body = client.get("/budget/alert", params={"year": 2026, "month": 6}).json()
    assert body["spent"] == 65
    assert body["over_limit"] is True
    assert body["over_by"] == 15


def test_alert_excludes_other_months(client: TestClient) -> None:
    client.put("/budget/monthly-limit", json={"amount": 100})
    _add(client, 80, "2026-06-10")
    _add(client, 200, "2026-05-10")
    body = client.get("/budget/alert", params={"year": 2026, "month": 6}).json()
    assert body["spent"] == 80
    assert body["over_limit"] is False


def test_alert_without_limit_returns_404(client: TestClient) -> None:
    resp = client.get("/budget/alert", params={"year": 2026, "month": 6})
    assert resp.status_code == 404


def test_set_limit_rejects_negative(client: TestClient) -> None:
    resp = client.put("/budget/monthly-limit", json={"amount": -5})
    assert resp.status_code == 422
