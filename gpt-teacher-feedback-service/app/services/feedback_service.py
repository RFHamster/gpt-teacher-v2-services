import logging
from datetime import datetime, timezone

from sqlmodel import select

from app.core.db import get_session

from gpt_teacher_db.gpt_teacher.models.chat_message import ChatMessage
from gpt_teacher_db.gpt_teacher.models.student_session import StudentSession
from gpt_teacher_db.gpt_teacher.models.problem import Problem
from gpt_teacher_db.gpt_teacher.models.classroom import Classroom
from gpt_teacher_db.gpt_teacher.enum import MessageType

logger = logging.getLogger("feedback_service")
logging.basicConfig(level=logging.INFO)


def generate_feedback_report() -> None:
    """
    Ponto de entrada da BackgroundTask.

    Não recebe nenhum dado por parâmetro de propósito: abre sua
    própria sessão e lê tudo diretamente do banco, exatamente como
    um serviço independente/worker faria. Isso é o que permite, no
    futuro, trocar o disparo (hoje HTTP + BackgroundTask) por um
    consumidor de fila, sem mudar essa função.
    """
    logger.info("Iniciando geração de relatório de feedback...")

    with get_session() as session:
        classrooms = session.exec(select(Classroom)).all()

        for classroom in classrooms:
            problems = session.exec(
                select(Problem).where(Problem.classroom_id == classroom.id)
            ).all()
            problem_ids = [p.id for p in problems]

            if not problem_ids:
                continue

            student_sessions = session.exec(
                select(StudentSession).where(
                    StudentSession.problem_id.in_(problem_ids)
                )
            ).all()

            total_sessions = len(student_sessions)
            total_messages = 0
            total_student_messages = 0
            total_ai_messages = 0

            for student_session in student_sessions:
                messages = session.exec(
                    select(ChatMessage).where(
                        ChatMessage.session_id == student_session.id
                    )
                ).all()
                total_messages += len(messages)
                total_student_messages += sum(
                    1 for m in messages if m.type == MessageType.USER
                )
                total_ai_messages += sum(
                    1 for m in messages if m.type == MessageType.AI
                )

            logger.info(
                "Turma '%s' (%s): %d sessões, %d mensagens "
                "(%d do aluno, %d da IA)",
                classroom.name,
                classroom.id,
                total_sessions,
                total_messages,
                total_student_messages,
                total_ai_messages,
            )

    logger.info(
        "Relatório de feedback concluído em %s",
        datetime.now(timezone.utc).isoformat(),
    )
