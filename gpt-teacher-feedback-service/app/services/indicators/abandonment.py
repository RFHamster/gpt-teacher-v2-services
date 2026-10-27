"""Indicador 2: detecção de sessões abandonadas."""
from datetime import datetime, timezone

from gpt_teacher_db.gpt_teacher.enum import MessageType, SessionStatus
from gpt_teacher_db.gpt_teacher.models.chat_message import ChatMessage
from gpt_teacher_db.gpt_teacher.models.student_session import StudentSession


def _last_activity(
    session: StudentSession, messages: list[ChatMessage]
) -> datetime | None:
    """Retorna o timestamp da última atividade: última mensagem ou started_at."""
    student_msgs = [m for m in messages if m.type == MessageType.USER]
    if student_msgs and student_msgs[-1].created_at:
        return student_msgs[-1].created_at.replace(tzinfo=timezone.utc)
    if session.started_at:
        return session.started_at.replace(tzinfo=timezone.utc)
    return None


def check_abandonment(
    session: StudentSession,
    messages: list[ChatMessage],
    abandon_minutes: int,
) -> dict:
    """Verifica se uma sessão foi abandonada.

    Regra: status=OPEN + última atividade há mais de abandon_minutes.
    Campo closed_at existe no model (SessionStatus.CLOSED), então sessões
    CLOSED não são marcadas como abandonadas.
    """
    if session.status == SessionStatus.CLOSED:
        return {
            "session_id": str(session.id),
            "abandoned": False,
            "label": "completed",
            "idle_minutes": None,
            "last_activity": session.closed_at.isoformat() if session.closed_at else None,
        }

    last = _last_activity(session, messages)
    if last is None:
        return {
            "session_id": str(session.id),
            "abandoned": None,
            "label": "indefinido — sem timestamp de atividade",
            "idle_minutes": None,
            "last_activity": None,
        }

    now = datetime.now(timezone.utc)
    idle_minutes = (now - last).total_seconds() / 60

    if idle_minutes >= abandon_minutes:
        return {
            "session_id": str(session.id),
            "abandoned": True,
            "label": "provavelmente_abandonada",
            "idle_minutes": round(idle_minutes, 1),
            "last_activity": last.isoformat(),
            "note": (
                "Não há campo 'abandoned' explícito no schema. "
                "Rótulo baseado em inatividade; o professor deve confirmar."
            ),
        }

    return {
        "session_id": str(session.id),
        "abandoned": False,
        "label": "ativa_ou_recente",
        "idle_minutes": round(idle_minutes, 1),
        "last_activity": last.isoformat(),
    }
