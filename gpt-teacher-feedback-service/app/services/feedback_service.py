import logging
from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from sqlmodel import select

from app.core.config import settings
from app.core.db import get_session
from app.models.feedback import FeedbackReport
from app.services.indicators.abandonment import check_abandonment
from app.services.indicators.attempts import (
    attempts_per_session,
    attempts_per_student_problem,
)
from app.services.indicators.methodology import compare_methodologies
from app.services.indicators.session_evaluation import evaluate_session

from gpt_teacher_db.gpt_teacher.models.chat_message import ChatMessage
from gpt_teacher_db.gpt_teacher.models.classroom import Classroom
from gpt_teacher_db.gpt_teacher.models.classroom_student import ClassroomStudent
from gpt_teacher_db.gpt_teacher.models.problem import Problem
from gpt_teacher_db.gpt_teacher.models.student_session import StudentSession

logger = logging.getLogger("feedback_service")
logging.basicConfig(level=logging.INFO)


def _upsert_report(
    db,
    classroom_id: UUID,
    student_id: UUID | None,
    session_id: UUID | None,
    indicator_type: str,
    value: dict,
) -> None:
    existing = db.exec(
        select(FeedbackReport).where(
            FeedbackReport.classroom_id == classroom_id,
            FeedbackReport.student_id == student_id,
            FeedbackReport.session_id == session_id,
            FeedbackReport.indicator_type == indicator_type,
        )
    ).first()

    if existing:
        existing.value = value
        existing.generated_at = datetime.now(timezone.utc)
        db.add(existing)
    else:
        db.add(FeedbackReport(
            classroom_id=classroom_id,
            student_id=student_id,
            session_id=session_id,
            indicator_type=indicator_type,
            value=value,
        ))


def generate_feedback_report() -> None:
    """Ponto de entrada da BackgroundTask."""
    logger.info("Iniciando geração de relatório de feedback...")

    with get_session() as db:
        classrooms = db.exec(select(Classroom)).all()

        for classroom in classrooms:
            logger.info("Processando turma '%s' (%s)", classroom.name, classroom.id)

            problems = db.exec(
                select(Problem).where(Problem.classroom_id == classroom.id)
            ).all()
            problem_ids = [p.id for p in problems]

            if not problem_ids:
                continue

            classroom_students = db.exec(
                select(ClassroomStudent).where(
                    ClassroomStudent.classroom_id == classroom.id
                )
            ).all()
            methodology_by_student: dict[UUID, str] = {
                cs.student_id: cs.methodology.value
                for cs in classroom_students
            }

            student_sessions = db.exec(
                select(StudentSession).where(
                    StudentSession.problem_id.in_(problem_ids)
                )
            ).all()

            messages_by_session: dict[UUID, list[ChatMessage]] = defaultdict(list)
            if student_sessions:
                session_ids = [s.id for s in student_sessions]
                all_messages = db.exec(
                    select(ChatMessage).where(
                        ChatMessage.session_id.in_(session_ids)
                    )
                ).all()
                for msg in all_messages:
                    messages_by_session[msg.session_id].append(msg)

            sessions_by_student_problem: dict[tuple[UUID, UUID], list[StudentSession]] = defaultdict(list)
            for s in student_sessions:
                sessions_by_student_problem[(s.student_id, s.problem_id)].append(s)

            student_summary: list[dict] = []

            for s in student_sessions:
                msgs = messages_by_session[s.id]
                methodology = methodology_by_student.get(s.student_id)

                att = attempts_per_session(s, msgs)
                _upsert_report(db, classroom.id, s.student_id, s.id, "attempts_per_session", att)

                abn = check_abandonment(s, msgs, settings.ABANDON_MINUTES)
                _upsert_report(db, classroom.id, s.student_id, s.id, "abandonment", abn)

                # Avaliação holística via LLM: resolve acerto/erro, qualidade do código,
                # dependência de ajuda e pedido de resposta pronta em uma única chamada.
                ev = evaluate_session(s, msgs)
                _upsert_report(db, classroom.id, s.student_id, s.id, "session_evaluation", ev)

                student_summary.append({
                    "student_id": str(s.student_id),
                    "methodology": methodology,
                    "avg_attempts": att["student_message_count"],
                    "is_abandoned": abn.get("abandoned") is True,
                    "resolved": ev.get("resolved"),
                    "help_dependency": ev.get("help_dependency"),
                    "answer_seeking_detected": ev.get("answer_seeking_detected"),
                })

            for (student_id, problem_id), sessions in sessions_by_student_problem.items():
                agg = attempts_per_student_problem(
                    student_id, problem_id, sessions, messages_by_session
                )
                _upsert_report(db, classroom.id, student_id, None, "attempts_per_student_problem", agg)

            meth_comparison = compare_methodologies(classroom.id, student_summary)
            _upsert_report(db, classroom.id, None, None, "methodology_comparison", meth_comparison)

            db.commit()
            logger.info("Turma '%s' processada: %d sessões", classroom.name, len(student_sessions))

    logger.info(
        "Relatório de feedback concluído em %s",
        datetime.now(timezone.utc).isoformat(),
    )
