"""Testes unitários dos indicadores — sem banco de dados."""
from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from gpt_teacher_db.gpt_teacher.enum import MessageType, SessionStatus
from gpt_teacher_db.gpt_teacher.models.chat_message import ChatMessage
from gpt_teacher_db.gpt_teacher.models.student_session import StudentSession

from app.services.indicators.abandonment import check_abandonment
from app.services.indicators.answer_seeking import analyze_answer_seeking
from app.services.indicators.attempts import (
    attempts_per_session,
    attempts_per_student_problem,
)
from app.services.indicators.error_type import analyze_error_types, classify_error
from app.services.indicators.methodology import compare_methodologies
from app.services.indicators.stuck import check_stuck


# ---------------------------------------------------------------------------
# Helpers de fixture
# ---------------------------------------------------------------------------

_SENTINEL = object()


def make_session(
    status: SessionStatus = SessionStatus.OPEN,
    started_at: datetime | None | object = _SENTINEL,
    closed_at: datetime | None = None,
) -> StudentSession:
    now = datetime.now(timezone.utc)
    s = StudentSession(
        id=uuid4(),
        student_id=uuid4(),
        problem_id=uuid4(),
        status=status,
        started_at=now if started_at is _SENTINEL else started_at,
        closed_at=closed_at,
    )
    return s


def make_message(
    session_id,
    msg_type: MessageType = MessageType.USER,
    content: str = "minha dúvida",
    code: str | None = None,
    created_at: datetime | None = None,
) -> ChatMessage:
    now = datetime.now(timezone.utc)
    m = ChatMessage(
        id=uuid4(),
        session_id=session_id,
        problem_id=uuid4(),
        type=msg_type,
        content=content,
        code=code,
    )
    m.created_at = created_at or now
    return m


# ---------------------------------------------------------------------------
# Indicador 1 — tentativas por sessão
# ---------------------------------------------------------------------------

class TestAttemptsPerSession:
    def test_empty_session(self):
        s = make_session()
        result = attempts_per_session(s, [])
        assert result["student_message_count"] == 0
        assert result["ai_message_count"] == 0
        assert result["total_messages"] == 0

    def test_one_student_message(self):
        s = make_session()
        msgs = [make_message(s.id, MessageType.USER)]
        result = attempts_per_session(s, msgs)
        assert result["student_message_count"] == 1
        assert result["ai_message_count"] == 0

    def test_mixed_messages(self):
        s = make_session()
        msgs = [
            make_message(s.id, MessageType.USER),
            make_message(s.id, MessageType.AI),
            make_message(s.id, MessageType.USER),
            make_message(s.id, MessageType.AI),
            make_message(s.id, MessageType.USER),
        ]
        result = attempts_per_session(s, msgs)
        assert result["student_message_count"] == 3
        assert result["ai_message_count"] == 2


class TestAttemptsPerStudentProblem:
    def test_no_sessions(self):
        result = attempts_per_student_problem(uuid4(), uuid4(), [], {})
        assert result["session_count"] == 0
        assert result["total_student_messages"] == 0

    def test_multiple_sessions(self):
        sid = uuid4()
        pid = uuid4()
        s1 = make_session()
        s2 = make_session()
        msgs = {
            s1.id: [make_message(s1.id, MessageType.USER), make_message(s1.id, MessageType.USER)],
            s2.id: [make_message(s2.id, MessageType.USER)],
        }
        result = attempts_per_student_problem(sid, pid, [s1, s2], msgs)
        assert result["session_count"] == 2
        assert result["total_student_messages"] == 3


# ---------------------------------------------------------------------------
# Indicador 2 — abandono
# ---------------------------------------------------------------------------

class TestAbandonment:
    def test_closed_session_not_abandoned(self):
        s = make_session(status=SessionStatus.CLOSED, closed_at=datetime.now(timezone.utc))
        result = check_abandonment(s, [], abandon_minutes=30)
        assert result["abandoned"] is False
        assert result["label"] == "completed"

    def test_open_session_recent_not_abandoned(self):
        s = make_session(status=SessionStatus.OPEN, started_at=datetime.now(timezone.utc))
        msgs = [make_message(s.id, created_at=datetime.now(timezone.utc))]
        result = check_abandonment(s, msgs, abandon_minutes=30)
        assert result["abandoned"] is False

    def test_open_session_old_is_abandoned(self):
        old = datetime.now(timezone.utc) - timedelta(minutes=60)
        s = make_session(status=SessionStatus.OPEN, started_at=old)
        msgs = [make_message(s.id, created_at=old)]
        result = check_abandonment(s, msgs, abandon_minutes=30)
        assert result["abandoned"] is True
        assert result["label"] == "provavelmente_abandonada"
        assert result["idle_minutes"] >= 60

    def test_open_session_no_messages_no_timestamp(self):
        s = make_session(status=SessionStatus.OPEN, started_at=None)
        result = check_abandonment(s, [], abandon_minutes=30)
        assert result["abandoned"] is None
        assert "indefinido" in result["label"]


# ---------------------------------------------------------------------------
# Indicador 3 — aluno travado
# ---------------------------------------------------------------------------

class TestStuck:
    def test_empty_session_not_stuck(self):
        s = make_session()
        result = check_stuck(s, [], stuck_messages=5, similarity_ratio=0.7)
        assert result["is_stuck"] is False
        assert result["reasons"] == []

    def test_many_messages_triggers_stuck(self):
        s = make_session()
        msgs = [make_message(s.id, content=f"tentativa {i}") for i in range(6)]
        result = check_stuck(s, msgs, stuck_messages=5, similarity_ratio=0.7)
        assert result["is_stuck"] is True
        types = [r["type"] for r in result["reasons"]]
        assert "many_messages" in types

    def test_frustration_keyword_detected(self):
        s = make_session()
        msgs = [make_message(s.id, content="não consigo resolver esse problema")]
        result = check_stuck(s, msgs, stuck_messages=5, similarity_ratio=0.7)
        assert result["is_stuck"] is True
        types = [r["type"] for r in result["reasons"]]
        assert "frustration_keywords" in types

    def test_repetitive_messages(self):
        s = make_session()
        same = "como faço para somar os elementos da lista"
        msgs = [
            make_message(s.id, content=same),
            make_message(s.id, content=same + " por favor"),
        ]
        result = check_stuck(s, msgs, stuck_messages=5, similarity_ratio=0.7)
        assert result["is_stuck"] is True
        types = [r["type"] for r in result["reasons"]]
        assert "repetitive_messages" in types

    def test_no_code_change(self):
        s = make_session()
        code = "x = 1\nprint(x)"
        msgs = [
            make_message(s.id, code=code),
            make_message(s.id, code=code),
        ]
        result = check_stuck(s, msgs, stuck_messages=5, similarity_ratio=0.7)
        assert result["is_stuck"] is True
        types = [r["type"] for r in result["reasons"]]
        assert "no_code_change" in types


# ---------------------------------------------------------------------------
# Indicador 4 — pedido de resposta pronta
# ---------------------------------------------------------------------------

class TestAnswerSeeking:
    def test_no_answer_seeking(self):
        s = make_session()
        msgs = [make_message(s.id, content="qual é o erro no meu código?")]
        result = analyze_answer_seeking(s, msgs, methodology="socratic")
        assert result["answer_seeking_count"] == 0
        assert result["answer_seeking_rate"] == 0.0

    def test_detects_pattern(self):
        s = make_session()
        msgs = [make_message(s.id, content="me dá a resposta logo")]
        result = analyze_answer_seeking(s, msgs, methodology="socratic")
        assert result["answer_seeking_count"] == 1
        assert result["answer_seeking_rate"] == 1.0
        assert result["detections"][0]["matched_pattern"] == "me_da_resposta"

    def test_empty_session(self):
        s = make_session()
        result = analyze_answer_seeking(s, [], methodology=None)
        assert result["answer_seeking_count"] == 0
        assert result["total_student_messages"] == 0

    def test_multiple_patterns(self):
        s = make_session()
        msgs = [
            make_message(s.id, content="faz pra mim esse código"),
            make_message(s.id, content="explica o erro aqui"),
            make_message(s.id, content="resolve isso por favor"),
        ]
        result = analyze_answer_seeking(s, msgs, methodology="direct")
        assert result["answer_seeking_count"] == 2
        assert 0.6 < result["answer_seeking_rate"] < 0.7

    def test_methodology_stored_in_detection(self):
        s = make_session()
        msgs = [make_message(s.id, content="me passa o código completo")]
        result = analyze_answer_seeking(s, msgs, methodology="step_by_step")
        assert result["detections"][0]["methodology_at_time"] == "step_by_step"


# ---------------------------------------------------------------------------
# Indicador 5 — tipo de erro
# ---------------------------------------------------------------------------

class TestErrorType:
    def _msg(self, content: str, code_review: str | None = None) -> ChatMessage:
        s_id = uuid4()
        m = ChatMessage(
            id=uuid4(), session_id=s_id, problem_id=uuid4(),
            type=MessageType.USER, content=content, code_review=code_review,
        )
        return m

    def test_syntax_error(self):
        m = self._msg("aparece SyntaxError na linha 5")
        result = classify_error(m)
        assert result["category"] == "syntax"

    def test_index_error(self):
        m = self._msg("IndexError: list index out of range")
        result = classify_error(m)
        assert result["category"] == "index_error"

    def test_type_error(self):
        m = self._msg("TypeError: só tenho um int e um str")
        result = classify_error(m)
        assert result["category"] == "type_error"

    def test_frustration_falls_to_other(self):
        m = self._msg("não sei o que fazer aqui")
        result = classify_error(m)
        assert result["category"] in ("other", "scope_error", "logic_error")

    def test_high_confidence_two_keywords(self):
        m = self._msg("loop infinito, o laço não para nunca")
        result = classify_error(m)
        assert result["category"] == "loop_error"
        assert result["confidence"] == "high"

    def test_empty_message(self):
        m = self._msg("")
        result = classify_error(m)
        assert result["category"] == "other"

    def test_aggregate_counts(self):
        msgs = [
            make_message(uuid4(), content="SyntaxError aqui"),
            make_message(uuid4(), content="IndexError nessa linha"),
            make_message(uuid4(), content="outro SyntaxError"),
        ]
        result = analyze_error_types(msgs)
        assert result["category_counts"].get("syntax", 0) >= 2
        assert result["total_classified"] == 3


# ---------------------------------------------------------------------------
# Indicador 6 — comparação entre metodologias
# ---------------------------------------------------------------------------

class TestMethodologyComparison:
    def test_empty_students(self):
        result = compare_methodologies(uuid4(), [])
        for meth in ("socratic", "direct", "step_by_step"):
            assert result["methodology_groups"][meth]["n"] == 0
        assert "descritiva" in result["warning"]

    def test_groups_calculated(self):
        students = [
            {"student_id": str(uuid4()), "methodology": "socratic",
             "avg_attempts": 4, "is_abandoned": False,
             "resolved": False, "help_dependency": "high", "answer_seeking_detected": True},
            {"student_id": str(uuid4()), "methodology": "socratic",
             "avg_attempts": 6, "is_abandoned": True,
             "resolved": True, "help_dependency": "low", "answer_seeking_detected": False},
            {"student_id": str(uuid4()), "methodology": "direct",
             "avg_attempts": 2, "is_abandoned": False,
             "resolved": True, "help_dependency": "medium", "answer_seeking_detected": False},
        ]
        result = compare_methodologies(uuid4(), students)
        assert result["methodology_groups"]["socratic"]["n"] == 2
        assert result["methodology_groups"]["direct"]["n"] == 1
        assert result["methodology_groups"]["step_by_step"]["n"] == 0
        assert result["methodology_groups"]["socratic"]["avg_attempts"] == 5.0
        assert result["methodology_groups"]["socratic"]["abandonment_rate"] == 0.5
        assert result["methodology_groups"]["socratic"]["high_dependency_rate"] == 0.5
        assert result["methodology_groups"]["socratic"]["answer_seeking_rate"] == 0.5
        assert result["methodology_groups"]["socratic"]["resolution_rate"] == 0.5

    def test_student_without_methodology_defaults_to_socratic(self):
        students = [
            {"student_id": str(uuid4()), "methodology": None,
             "avg_attempts": 3, "is_abandoned": False,
             "resolved": True, "help_dependency": "low", "answer_seeking_detected": False},
        ]
        result = compare_methodologies(uuid4(), students)
        assert result["methodology_groups"]["socratic"]["n"] == 1
