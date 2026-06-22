from fastapi import FastAPI

from app.database import init_db
from app.routes import budget_router, router


def create_app() -> FastAPI:
    app = FastAPI(title="Expense API")
    app.include_router(router)
    app.include_router(budget_router)

    @app.on_event("startup")
    def _startup() -> None:
        init_db()

    return app


app = create_app()
