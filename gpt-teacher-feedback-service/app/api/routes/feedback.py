from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlmodel import Session, select

from app.core.db import get_session
from app.core.security import require_api_key
from app.models.feedback import FeedbackReport
from app.services.feedback_service import generate_feedback_report

from gpt_teacher_db.gpt_teacher.models.classroom import Classroom

router = APIRouter(tags=["feedback"])


@router.post(
    "/feedback/generate",
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_feedback_generation(background_tasks: BackgroundTasks):
    """Dispara a geração do relatório de feedback em segundo plano.

    Retorna imediatamente (202 Accepted) e a leitura/processamento
    do banco acontece de forma assíncrona, depois da resposta HTTP
    já ter sido enviada.
    """
    background_tasks.add_task(generate_feedback_report)
    return {"message": "Geração de feedback iniciada em segundo plano."}


def _get_db():
    with get_session() as session:
        yield session


def _verify_classroom_ownership(
    classroom_id: UUID,
    teacher_id: UUID,
    db: Session,
) -> Classroom:
    classroom = db.exec(
        select(Classroom).where(Classroom.id == classroom_id)
    ).first()
    if not classroom:
        raise HTTPException(status_code=404, detail="Turma não encontrada.")
    if classroom.teacher_id != teacher_id:
        raise HTTPException(
            status_code=403,
            detail="Acesso negado: você não é o professor desta turma.",
        )
    return classroom


@router.get(
    "/feedback/classrooms/{classroom_id}/summary",
    dependencies=[Depends(require_api_key)],
)
def get_classroom_summary(
    classroom_id: UUID,
    teacher_id: UUID,
    db: Session = Depends(_get_db),
):
    """Indicadores agregados da turma + comparação entre metodologias.

    teacher_id: UUID do professor autenticado (enviado pelo backend principal).
    """
    _verify_classroom_ownership(classroom_id, teacher_id, db)

    reports = db.exec(
        select(FeedbackReport).where(
            FeedbackReport.classroom_id == classroom_id
        )
    ).all()

    if not reports:
        return {"classroom_id": str(classroom_id), "indicators": [], "message": "Nenhum relatório gerado ainda."}

    result: dict = {"classroom_id": str(classroom_id), "indicators": {}}
    for r in reports:
        if r.student_id is None and r.session_id is None:
            result["indicators"][r.indicator_type] = r.value

    result["generated_at"] = (
        max(r.generated_at for r in reports).isoformat()
        if reports else None
    )
    return result


@router.get(
    "/feedback/classrooms/{classroom_id}/students/{student_id}",
    dependencies=[Depends(require_api_key)],
)
def get_student_indicators(
    classroom_id: UUID,
    student_id: UUID,
    teacher_id: UUID,
    db: Session = Depends(_get_db),
):
    """Indicadores do aluno dentro de uma turma.

    teacher_id: UUID do professor autenticado (enviado pelo backend principal).
    """
    _verify_classroom_ownership(classroom_id, teacher_id, db)

    reports = db.exec(
        select(FeedbackReport).where(
            FeedbackReport.classroom_id == classroom_id,
            FeedbackReport.student_id == student_id,
        )
    ).all()

    if not reports:
        return {
            "classroom_id": str(classroom_id),
            "student_id": str(student_id),
            "indicators": [],
            "message": "Nenhum relatório gerado para este aluno.",
        }

    by_session: dict = {}
    aggregated: dict = {}
    for r in reports:
        if r.session_id:
            by_session.setdefault(str(r.session_id), {})[r.indicator_type] = r.value
        else:
            aggregated[r.indicator_type] = r.value

    return {
        "classroom_id": str(classroom_id),
        "student_id": str(student_id),
        "aggregated": aggregated,
        "by_session": by_session,
    }


@router.get(
    "/feedback/sessions/{session_id}",
    dependencies=[Depends(require_api_key)],
)
def get_session_detail(
    session_id: UUID,
    teacher_id: UUID,
    db: Session = Depends(_get_db),
):
    """Detalhe de uma sessão: travado, abandonada, respostas prontas, tipos de erro.

    teacher_id: UUID do professor autenticado (enviado pelo backend principal).
    Verifica que a sessão pertence a uma turma do professor.
    """
    reports = db.exec(
        select(FeedbackReport).where(
            FeedbackReport.session_id == session_id
        )
    ).first()

    if not reports:
        raise HTTPException(status_code=404, detail="Sessão não encontrada ou sem relatório gerado.")

    classroom_id = reports.classroom_id
    _verify_classroom_ownership(classroom_id, teacher_id, db)

    all_reports = db.exec(
        select(FeedbackReport).where(
            FeedbackReport.session_id == session_id
        )
    ).all()

    return {
        "session_id": str(session_id),
        "classroom_id": str(classroom_id),
        "indicators": {r.indicator_type: r.value for r in all_reports},
    }
