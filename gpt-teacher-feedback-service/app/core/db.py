from sqlmodel import Session, create_engine
from app.core.config import settings

engine = create_engine(settings.DATABASE_URI, echo=False)


def get_session() -> Session:
    """Cria uma sessão nova e independente. Use isto dentro de
    background tasks e serviços — nunca reaproveite a sessão de uma
    requisição HTTP já finalizada."""
    return Session(engine)
