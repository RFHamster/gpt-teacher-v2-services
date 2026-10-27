from sqlmodel import Session, SQLModel, create_engine
from app.core.config import settings

engine = create_engine(settings.DATABASE_URI, echo=False)


def get_session() -> Session:
    """Cria uma sessão nova e independente. Use isto dentro de
    background tasks e serviços — nunca reaproveite a sessão de uma
    requisição HTTP já finalizada."""
    return Session(engine)


def create_db_and_tables() -> None:
    """Cria as tabelas do feedback-service se ainda não existirem.
    Não toca no schema gpt_teacher — apenas cria tabelas com prefixo feedback_."""
    import app.models.feedback  # noqa: F401 — importar para registrar metadados
    SQLModel.metadata.create_all(engine)
