from fastapi import FastAPI

from app.api.routes import feedback

app = FastAPI(title="GPT Teacher — Feedback Service")

app.include_router(feedback.router, prefix="/api/v1")


@app.get("/health")
def health_check():
    return {"status": "ok"}
