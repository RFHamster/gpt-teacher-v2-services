from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import feedback
from app.core.db import create_db_and_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(title="GPT Teacher — Feedback Service", lifespan=lifespan)

app.include_router(feedback.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
