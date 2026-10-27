from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import JSON, Column, UniqueConstraint
from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class FeedbackReport(SQLModel, table=True):
    """Armazena o resultado calculado de um indicador de feedback.

    Granularidade variável: session_id preenchido = indicador por sessão;
    student_id sem session_id = indicador por aluno/problema; só classroom_id
    = indicador agregado de turma.

    Idempotência: upsert por (classroom_id, student_id, session_id, indicator_type).
    """

    __tablename__ = "feedback_report"
    __table_args__ = (
        UniqueConstraint(
            "classroom_id",
            "student_id",
            "session_id",
            "indicator_type",
            name="uq_feedback_report_key",
        ),
    )

    id: UUID = Field(default_factory=uuid4, primary_key=True)
    classroom_id: UUID = Field(index=True)
    student_id: Optional[UUID] = Field(default=None, index=True, nullable=True)
    session_id: Optional[UUID] = Field(default=None, index=True, nullable=True)
    indicator_type: str = Field(max_length=100, index=True)
    value: Any = Field(sa_column=Column(JSON, nullable=False))
    generated_at: datetime = Field(default_factory=_utcnow)
