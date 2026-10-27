"""Indicador 4: detecção de pedido de resposta pronta por mensagem."""
from gpt_teacher_db.gpt_teacher.enum import MessageType
from gpt_teacher_db.gpt_teacher.models.chat_message import ChatMessage
from gpt_teacher_db.gpt_teacher.models.student_session import StudentSession

from app.patterns.answer_seeking import find_answer_seeking_pattern


def analyze_answer_seeking(
    session: StudentSession,
    messages: list[ChatMessage],
    methodology: str | None,
) -> dict:
    """Detecta mensagens com pedido de resposta pronta e calcula taxa por sessão."""
    student_msgs = [m for m in messages if m.type == MessageType.USER]
    detections: list[dict] = []

    for msg in student_msgs:
        matched = find_answer_seeking_pattern(msg.content)
        if matched:
            detections.append({
                "message_id": str(msg.id),
                "snippet": msg.content[:200],
                "matched_pattern": matched.name,
                "methodology_at_time": methodology,
            })

    total = len(student_msgs)
    rate = len(detections) / total if total > 0 else 0.0

    return {
        "session_id": str(session.id),
        "answer_seeking_count": len(detections),
        "total_student_messages": total,
        "answer_seeking_rate": round(rate, 4),
        "detections": detections,
        "note": (
            "Falso positivo é possível. O professor deve ler o contexto "
            "antes de qualquer interpretação."
        ),
    }
