"""Exercises the real Step 8 question generation + Step 8A validation flow
against a real Postgres instance (see README.md "Testing"). Only the Mistral
call is mocked — repositories, DB writes, and validation logic are real.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from question_generation_service.core.config import get_settings
from question_generation_service.repositories.question_repository import QuestionRepository
from question_generation_service.schemas.question import QuestionGenerationRequest
from question_generation_service.services.question_service import QuestionService

pytestmark = pytest.mark.asyncio


def _draft(
    question_type: str = "MCQ",
    question_text: str = "What does the borrow checker enforce at compile time?",
    options: list[str] | None = None,
    correct_answer: str = "Ownership rules",
    explanation: str = "The borrow checker enforces Rust's ownership and borrowing rules.",
) -> dict[str, object]:
    return {
        "question_type": question_type,
        "question_text": question_text,
        "options": options
        if options is not None
        else ["Ownership rules", "Garbage collection", "Type inference", "Macros"],
        "correct_answer": correct_answer,
        "explanation": explanation,
        "estimated_time_seconds": 30,
        "tags": ["rust"],
    }


async def _insert_learning_unit(session, concept_id: uuid.UUID, thema: str) -> None:
    await session.execute(
        text(
            "INSERT INTO learning_units "
            "(id, thema, topic, concept_name, complexity_level, created_at) "
            "VALUES (:id, :thema, :topic, :concept_name, :complexity_level, now())"
        ),
        {
            "id": str(concept_id),
            "thema": thema,
            "topic": "Ownership",
            "concept_name": "Borrow checker",
            "complexity_level": "Medium",
        },
    )
    await session.commit()


async def test_generate_batch_fills_questions_and_validation_log(monkeypatch):
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        concept_id = uuid.uuid4()
        await _insert_learning_unit(session, concept_id, "Rust Ownership")

        repository = QuestionRepository(session)
        service = QuestionService(repository)

        # One clean question and one that fails validation (answer not in options),
        # so both the "stored" and "dropped" paths get exercised against the real DB.
        async def fake_chat_complete(system_msg, user_msg, config):
            return {
                "questions": [
                    _draft(),
                    _draft(
                        question_text="Does Rust use a garbage collector?",
                        question_type="TrueFalse",
                        options=["True", "False"],
                        correct_answer="Nope",  # not in options -> Failed
                        explanation="Rust does not use a garbage collector.",
                    ),
                ]
            }

        monkeypatch.setattr(
            "question_generation_service.services.question_service.chat_complete",
            fake_chat_complete,
        )

        request = QuestionGenerationRequest(
            concept_id=concept_id,
            concept_name="Borrow checker",
            learning_goal="Explain how the borrow checker enforces ownership",
            bloom_level="Understanding",
            difficulty_tier="medium",
        )

        result = await service.generate_batch(request)

        assert len(result.questions) == 1
        assert result.questions[0].validation_status == "Passed"

        stored_rows = (
            await session.execute(
                text(
                    "SELECT id, concept_id, bloom_level, difficulty_tier, question_type, "
                    "question_text, options, correct_answer, estimated_time, tags "
                    "FROM questions WHERE concept_id = :concept_id"
                ),
                {"concept_id": str(concept_id)},
            )
        ).all()
        assert len(stored_rows) == 1
        row = stored_rows[0]
        assert row.bloom_level == "Understanding"
        assert row.difficulty_tier == "medium"
        assert row.question_type == "MCQ"
        assert row.correct_answer == "Ownership rules"
        assert row.estimated_time == "30"
        assert row.tags == ["rust"]

        validation_rows = (
            await session.execute(
                text(
                    "SELECT question_id, validation_status, failed_checks, validation_score "
                    "FROM question_validation_log "
                    "WHERE question_id = :question_id OR (question_id IS NULL AND notes LIKE :notes)"
                ),
                {"question_id": str(row.id), "notes": "Does Rust use a garbage collector%"},
            )
        ).all()
        assert len(validation_rows) == 2
        statuses = {r.validation_status for r in validation_rows}
        assert statuses == {"Passed", "Failed"}

        passed_row = next(r for r in validation_rows if r.validation_status == "Passed")
        assert passed_row.question_id == row.id
        assert passed_row.failed_checks in (None, [])

        failed_row = next(r for r in validation_rows if r.validation_status == "Failed")
        assert failed_row.question_id is None
        assert "answer_in_options" in failed_row.failed_checks

    await engine.dispose()
