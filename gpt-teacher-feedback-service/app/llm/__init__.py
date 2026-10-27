from langchain_groq import ChatGroq

from app.core.config import settings

_MODEL = "openai/gpt-oss-20b"


def get_evaluator_model() -> ChatGroq:
    return ChatGroq(
        model=_MODEL,
        temperature=0,
        api_key=settings.GROQ_API_KEY,
    )
