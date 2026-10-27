"""Indicador 5: categorização do tipo de erro por palavras-chave.

Ponto de extensão: USE_LLM_ERROR_CLASSIFIER=True troca a lógica de
palavras-chave pela função _classify_with_llm (stub, não implementado).
"""
import re
from typing import Literal

from gpt_teacher_db.gpt_teacher.enum import MessageType
from gpt_teacher_db.gpt_teacher.models.chat_message import ChatMessage

ErrorCategory = Literal[
    "syntax", "type_error", "index_error", "loop_error",
    "logic_error", "scope_error", "io_error", "other",
]

_CATEGORY_KEYWORDS: dict[str, list[str]] = {
    "syntax": [
        r"syntax\s*error", r"syntaxerror", r"erro\s+de\s+sintaxe",
        r"unexpected\s+token", r"invalid\s+syntax", r"ponto\s+e\s+v[ií]rgula",
        r"faltou\s+fechar", r"parenteses", r"colchetes", r"chaves",
    ],
    "type_error": [
        r"typeerror", r"tipo\s+errado", r"type\s+error", r"int\s+e\s+str",
        r"n[aã]o\s+[eé]\s+um\s+n[uú]mero", r"concatenar", r"operandos",
    ],
    "index_error": [
        r"indexerror", r"list\s+index\s+out", r"[íi]ndice", r"index\s+out\s+of",
        r"out\s+of\s+range", r"fora\s+do\s+limite", r"posi[cç][aã]o",
    ],
    "loop_error": [
        r"\bloop\b", r"\bla[cç]o\b", r"\bfor\b.*\berro\b", r"\bwhile\b.*\berro\b",
        r"itera[cç][aã]o", r"repeti[cç][aã]o", r"n[aã]o\s+para",
        r"loop\s+infinito", r"la[cç]o\s+infinito",
    ],
    "logic_error": [
        r"resultado\s+errado", r"condi[cç][aã]o", r"\bif\b.*\berro\b",
        r"l[oó]gica", r"n[aã]o\s+entra\s+no\s+if", r"else\s+errado",
        r"compara[cç][aã]o", r"verdadeiro.*falso", r"falso.*verdadeiro",
    ],
    "scope_error": [
        r"nameerror", r"nome\s+n[aã]o\s+definido", r"not\s+defined",
        r"escopo", r"vari[aá]vel\s+n[aã]o\s+existe", r"undeclared",
        r"fora\s+do\s+escopo", r"n[aã]o\s+foi\s+declarad",
    ],
    "io_error": [
        r"\binput\b", r"\bprint\b.*\berro\b", r"entrada.*sa[ií]da",
        r"leitura", r"ioerror", r"n[aã]o\s+l[eê]\s+o\s+valor",
        r"n[aã]o\s+imprime",
    ],
}

_COMPILED: dict[str, list[re.Pattern]] = {
    cat: [re.compile(kw, re.IGNORECASE) for kw in kws]
    for cat, kws in _CATEGORY_KEYWORDS.items()
}


def _classify_by_keywords(text: str) -> tuple[ErrorCategory, str]:
    scores: dict[str, int] = {}
    for cat, patterns in _COMPILED.items():
        count = sum(1 for p in patterns if p.search(text))
        if count > 0:
            scores[cat] = count

    if not scores:
        return "other", "low"

    best_cat = max(scores, key=lambda c: scores[c])
    confidence = "high" if scores[best_cat] >= 2 else "low"
    return best_cat, confidence  # type: ignore[return-value]


def _classify_with_llm(text: str) -> tuple[ErrorCategory, str]:
    raise NotImplementedError("Classificador LLM ainda não implementado.")


def classify_error(message: ChatMessage, use_llm: bool = False) -> dict:
    """Classifica o tipo de erro em uma mensagem do aluno.

    Combina content + code_review para maximizar sinal.
    """
    text = message.content
    if message.code_review:
        text = text + " " + message.code_review

    if use_llm:
        category, confidence = _classify_with_llm(text)
    else:
        category, confidence = _classify_by_keywords(text)

    return {
        "message_id": str(message.id),
        "category": category,
        "confidence": confidence,
        "classifier": "llm" if use_llm else "keywords",
    }


def analyze_error_types(
    messages: list[ChatMessage],
    use_llm: bool = False,
) -> dict:
    """Classifica todos os erros de uma sessão e agrega por categoria."""
    student_msgs = [m for m in messages if m.type == MessageType.USER]
    classifications = [classify_error(m, use_llm=use_llm) for m in student_msgs]

    counts: dict[str, int] = {}
    for c in classifications:
        counts[c["category"]] = counts.get(c["category"], 0) + 1

    return {
        "total_classified": len(classifications),
        "category_counts": counts,
        "per_message": classifications,
    }
