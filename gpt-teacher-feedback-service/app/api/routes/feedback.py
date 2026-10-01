from fastapi import APIRouter, BackgroundTasks, status

from app.services.feedback_service import generate_feedback_report

router = APIRouter(tags=["feedback"])


@router.post(
    "/feedback/generate",
    status_code=status.HTTP_202_ACCEPTED,
)
def trigger_feedback_generation(background_tasks: BackgroundTasks):
    """
    Dispara a geração do relatório de feedback em segundo plano.

    Retorna imediatamente (202 Accepted) e a leitura/processamento
    do banco acontece de forma assíncrona, depois da resposta HTTP
    já ter sido enviada.
    """
    background_tasks.add_task(generate_feedback_report)
    return {"message": "Geração de feedback iniciada em segundo plano."}
