from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.database import init_db
from app.routes import budget_router, router


def create_app() -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        init_db()
        yield

    app = FastAPI(title="Expense API", lifespan=lifespan)
    app.include_router(router)
    app.include_router(budget_router)
    return app


app = create_app()
