from collections.abc import Iterator

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.database import get_connection, init_db
from app.routes import budget_router, get_db, router


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    db_path = tmp_path / "test.db"
    init_db(db_path)

    def override_get_db():
        with get_connection(db_path) as conn:
            yield conn

    app = FastAPI()
    app.include_router(router)
    app.include_router(budget_router)
    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
