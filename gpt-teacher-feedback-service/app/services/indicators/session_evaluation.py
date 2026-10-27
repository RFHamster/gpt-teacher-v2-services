"""Indicador: avaliação holística da sessão via LLM.

Substitui answer_seeking (regex), error_types (keywords) e stuck (keywords)
por uma única chamada ao Groq que lê toda a conversa e avalia em 4 dimensões.
"""
import logging
from typing import Literal

from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field

from gpt_teacher_db.gpt_teacher.enum import MessageType
from gpt_teacher_db.gpt_teacher.models.chat_message import ChatMessage
from gpt_teacher_db.gpt_teacher.models.student_session import StudentSession

from app.llm import get_evaluator_model

logger = logging.getLogger("feedback_service")

_SYSTEM_PROMPT = """Você é um avaliador pedagógico especializado em ensino de programação.

Analise a conversa abaixo entre um aluno e um assistente de ensino.
Avalie com base em TODA a conversa — não em mensagens isoladas.

Retorne uma avaliação estruturada nos 4 critérios abaixo:

1. RESOLUÇÃO: O aluno chegou à solução correta ao final?
   - complete: resolveu o problema, código funcional e correto
   - partial: avançou mas não chegou ao fim, ou chegou com erros graves
   - none: não avançou de forma significativa

2. QUALIDADE DO CÓDIGO: Avalie o último código enviado pelo aluno (0–10).
   - 0: sem código, ou completamente incorreto/ininteligível
   - 5: funciona mas sem boas práticas (nomes ruins, código duplicado, etc.)
   - 10: correto, legível, bem estruturado

3. DEPENDÊNCIA DE AJUDA:
   - low: o aluno avançou por conta própria, usando dicas como confirmaçã
   - medium: precisou de dicas para desbloquear a maior parte dos passos
   - high: dependeu do assistente em cada etapa, sem progresso autônomo

4. PEDIDO DE RESPOSTA PRONTA: O aluno pediu o código/resposta pronta
   em vez de tentar resolver? Conte quantas vezes fez isso explicitamente
   (incluindo formas indiretas como "só me mostra como faz", "faz pra mim", etc.)
"""


class _SessionEvaluation(BaseModel):
    resolved: bool = Field(description="O aluno resolveu o problema?")
    resolution_quality: Literal["complete", "partial", "none"] = Field(
        description="Qualidade da resolução: complete, partial ou none"
    )
    code_quality_score: int = Field(ge=0, le=10, description="Nota do código final (0-10)")
    code_quality_notes: str = Field(description="Observações sobre o código (1-2 frases)")
    help_dependency: Literal["low", "medium", "high"] = Field(
        description="Nível de dependência de ajuda: low, medium ou high"
    )
    help_dependency_notes: str = Field(description="O que motivou essa classificação (1-2 frases)")
    answer_seeking_detected: bool = Field(description="O aluno pediu resposta/código pronto?")
    answer_seeking_count: int = Field(ge=0, description="Quantas vezes pediu resposta pronta")
    answer_seeking_notes: str = Field(description="Contexto dos pedidos, ou 'Nenhum detectado'")
    summary: str = Field(description="Resumo geral do desempenho do aluno em 2-3 frases")


def _format_conversation(messages: list[ChatMessage]) -> str:
    sorted_msgs = sorted(messages, key=lambda m: m.created_at)
    parts: list[str] = []
    for msg in sorted_msgs:
        role = "ALUNO" if msg.type == MessageType.USER else "ASSISTENTE"
        parts.append(f"[{role}]: {msg.content}")
        if msg.type == MessageType.USER and msg.code:
            parts.append(f"[CÓDIGO DO ALUNO]:\n```\n{msg.code}\n```")
    return "\n\n".join(parts)


def evaluate_session(
    session: StudentSession,
    messages: list[ChatMessage],
) -> dict:
    """Envia a conversa completa ao Groq e retorna avaliação estruturada."""
    if not messages:
        return _empty_result(session)

    conversation = _format_conversation(messages)

    try:
        model = get_evaluator_model().with_structured_output(_SessionEvaluation)
        result: _SessionEvaluation = model.invoke([
            SystemMessage(content=_SYSTEM_PROMPT),
            HumanMessage(content=f"Conversa da sessão:\n\n{conversation}"),
        ])
        return {
            "session_id": str(session.id),
            "resolved": result.resolved,
            "resolution_quality": result.resolution_quality,
            "code_quality_score": result.code_quality_score,
            "code_quality_notes": result.code_quality_notes,
            "help_dependency": result.help_dependency,
            "help_dependency_notes": result.help_dependency_notes,
            "answer_seeking_detected": result.answer_seeking_detected,
            "answer_seeking_count": result.answer_seeking_count,
            "answer_seeking_notes": result.answer_seeking_notes,
            "summary": result.summary,
            "evaluated_by": "llm",
        }
    except Exception as exc:
        logger.warning("LLM evaluation failed for session %s: %s", session.id, exc)
        return _empty_result(session, error=str(exc))


def _empty_result(session: StudentSession, error: str | None = None) -> dict:
    return {
        "session_id": str(session.id),
        "resolved": None,
        "resolution_quality": "none",
        "code_quality_score": None,
        "code_quality_notes": "",
        "help_dependency": None,
        "help_dependency_notes": "",
        "answer_seeking_detected": None,
        "answer_seeking_count": 0,
        "answer_seeking_notes": "",
        "summary": "",
        "evaluated_by": "skipped",
        **({"error": error} if error else {}),
    }
