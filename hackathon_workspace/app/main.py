from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import db
from app.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Expense API", lifespan=lifespan)
app.include_router(router)
