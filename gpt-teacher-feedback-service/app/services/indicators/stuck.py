"""Indicador 3: aluno travado — lista de motivos, nunca só booleano."""
import re
from datetime import timezone

from gpt_teacher_db.gpt_teacher.enum import MessageType
from gpt_teacher_db.gpt_teacher.models.chat_message import ChatMessage
from gpt_teacher_db.gpt_teacher.models.student_session import StudentSession

_FRUSTRATION_PATTERNS = re.compile(
    r"n[aã]o\s+consigo|n[aã]o\s+entendo|desisto|n[aã]o\s+sei|"
    r"t[oô]\s+travad[oa]|estou\s+travad[oa]|n[aã]o\s+funciona|"
    r"n[aã]o\s+t[oô]\s+conseguindo|odeio|imposs[ií]vel|n[aã]o\s+consigo\s+resolver",
    re.IGNORECASE,
)


def _similarity_ratio(a: str, b: str) -> float:
    """Razão de palavras em comum entre duas strings (Jaccard simples)."""
    set_a = set(a.lower().split())
    set_b = set(b.lower().split())
    if not set_a and not set_b:
        return 1.0
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def check_stuck(
    session: StudentSession,
    messages: list[ChatMessage],
    stuck_messages: int,
    similarity_ratio: float,
) -> dict:
    """Retorna lista de motivos pelos quais o aluno pode estar travado.

    Motivos possíveis:
    - many_messages: muitas mensagens na sessão sem progresso
    - repetitive_messages: mensagens muito parecidas repetidas
    - frustration_keywords: expressões de frustração detectadas
    - no_code_change: código enviado não muda entre mensagens consecutivas
    """
    student_msgs = [m for m in messages if m.type == MessageType.USER]
    reasons: list[dict] = []

    if len(student_msgs) >= stuck_messages:
        reasons.append({
            "type": "many_messages",
            "detail": f"{len(student_msgs)} mensagens do aluno nesta sessão (limite: {stuck_messages})",
        })

    for i in range(1, len(student_msgs)):
        ratio = _similarity_ratio(
            student_msgs[i - 1].content, student_msgs[i].content
        )
        if ratio >= similarity_ratio:
            reasons.append({
                "type": "repetitive_messages",
                "detail": (
                    f"Mensagens {i} e {i+1} muito parecidas "
                    f"(similaridade: {ratio:.0%})"
                ),
                "msg_a": student_msgs[i - 1].content[:120],
                "msg_b": student_msgs[i].content[:120],
            })

    for msg in student_msgs:
        if _FRUSTRATION_PATTERNS.search(msg.content):
            reasons.append({
                "type": "frustration_keywords",
                "detail": "Expressão de frustração detectada na mensagem.",
                "snippet": msg.content[:200],
            })

    codes = [m.code for m in student_msgs if m.code]
    if len(codes) >= 2:
        for i in range(1, len(codes)):
            if codes[i - 1].strip() == codes[i].strip():
                reasons.append({
                    "type": "no_code_change",
                    "detail": f"Código idêntico em tentativas consecutivas ({i} e {i+1}).",
                })

    return {
        "session_id": str(session.id),
        "is_stuck": len(reasons) > 0,
        "reasons": reasons,
        "student_message_count": len(student_msgs),
        "note": (
            "Indicadores de 'travado' são sinais para o professor avaliar, "
            "nunca punição automática."
        ),
    }
