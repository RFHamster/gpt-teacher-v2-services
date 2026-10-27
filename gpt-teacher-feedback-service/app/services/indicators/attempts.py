"""Indicadores 1: quantidade de tentativas por sessão e por aluno+problema."""
from uuid import UUID

from gpt_teacher_db.gpt_teacher.enum import MessageType
from gpt_teacher_db.gpt_teacher.models.chat_message import ChatMessage
from gpt_teacher_db.gpt_teacher.models.student_session import StudentSession


def attempts_per_session(
    session: StudentSession,
    messages: list[ChatMessage],
) -> dict:
    """Conta mensagens do aluno e da IA em uma sessão."""
    student_msgs = [m for m in messages if m.type == MessageType.USER]
    ai_msgs = [m for m in messages if m.type == MessageType.AI]
    return {
        "session_id": str(session.id),
        "student_id": str(session.student_id),
        "problem_id": str(session.problem_id),
        "student_message_count": len(student_msgs),
        "ai_message_count": len(ai_msgs),
        "total_messages": len(messages),
    }


def attempts_per_student_problem(
    student_id: UUID,
    problem_id: UUID,
    sessions: list[StudentSession],
    all_messages_by_session: dict[UUID, list[ChatMessage]],
) -> dict:
    """Agrega sessões e mensagens de um aluno para um problema específico."""
    total_student_msgs = 0
    for s in sessions:
        msgs = all_messages_by_session.get(s.id, [])
        total_student_msgs += sum(1 for m in msgs if m.type == MessageType.USER)
    return {
        "student_id": str(student_id),
        "problem_id": str(problem_id),
        "session_count": len(sessions),
        "total_student_messages": total_student_msgs,
    }
