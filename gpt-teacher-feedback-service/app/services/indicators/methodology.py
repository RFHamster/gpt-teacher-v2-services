"""Indicador 6: comparação entre metodologias por turma."""
from uuid import UUID

from gpt_teacher_db.gpt_teacher.enum import TeachingMethodology


def compare_methodologies(
    classroom_id: UUID,
    student_indicators: list[dict],
) -> dict:
    """Agrupa indicadores por metodologia e calcula médias.

    student_indicators: lista de dicts com campos:
        student_id, methodology, avg_attempts, is_abandoned,
        resolved, help_dependency, answer_seeking_detected
    """
    groups: dict[str, list[dict]] = {m.value: [] for m in TeachingMethodology}

    for s in student_indicators:
        meth = s.get("methodology") or TeachingMethodology.SOCRATIC.value
        if meth not in groups:
            groups[meth] = []
        groups[meth].append(s)

    result: dict[str, dict] = {}
    for meth, students in groups.items():
        n = len(students)
        if n == 0:
            result[meth] = {"n": 0}
            continue

        result[meth] = {
            "n": n,
            "avg_attempts": round(
                sum(s.get("avg_attempts", 0) for s in students) / n, 2
            ),
            "abandonment_rate": round(
                sum(1 for s in students if s.get("is_abandoned")) / n, 4
            ),
            "resolution_rate": round(
                sum(1 for s in students if s.get("resolved")) / n, 4
            ),
            "high_dependency_rate": round(
                sum(1 for s in students if s.get("help_dependency") == "high") / n, 4
            ),
            "answer_seeking_rate": round(
                sum(1 for s in students if s.get("answer_seeking_detected")) / n, 4
            ),
        }

    return {
        "classroom_id": str(classroom_id),
        "methodology_groups": result,
        "warning": (
            "O aluno escolhe a própria metodologia, então a comparação "
            "é descritiva, não causal."
        ),
    }
