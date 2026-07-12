"""Exercises the real Step 8 question generation + Step 8A validation flow
against a real Postgres instance (see README.md "Testing"). Only the Mistral
call is mocked — repositories, DB writes, and validation logic are real.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from memosphere_domain import ALL_QUESTION_TYPES
from question_generation_service.core.config import get_settings
from question_generation_service.prompts.question_generation import build_prompt_3_system
from question_generation_service.prompts.question_judge import PROMPT_4_SYSTEM
from question_generation_service.repositories.question_repository import QuestionRepository
from question_generation_service.schemas.question import QuestionGenerationRequest
from question_generation_service.services.question_service import QuestionService

pytestmark = pytest.mark.asyncio

# The request built below never overrides allowed_question_types, so it's
# always generated under the default (unrestricted) prompt.
PROMPT_3_SYSTEM = build_prompt_3_system(ALL_QUESTION_TYPES)


def _draft(
    question_type: str = "MCQ",
    question_text: str = "What does the borrow checker enforce at compile time?",
    options: list[str] | None = None,
    correct_answers: list[str] | None = None,
    explanation: str = "The borrow checker enforces Rust's ownership and borrowing rules.",
) -> dict[str, object]:
    return {
        "question_type": question_type,
        "question_text": question_text,
        "options": options
        if options is not None
        else ["Ownership rules", "Garbage collection", "Type inference", "Macros"],
        "correct_answers": correct_answers if correct_answers is not None else ["Ownership rules"],
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


async def _insert_user(session, user_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (:user_id, :name, :email, now())"
        ),
        {"user_id": str(user_id), "name": "Test User", "email": f"{user_id}@example.com"},
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
        user_id = uuid.uuid4()
        await _insert_learning_unit(session, concept_id, "Rust Ownership")
        await _insert_user(session, user_id)

        try:
            repository = QuestionRepository(session)
            service = QuestionService(repository)

            # One clean question and one that fails structural validation (answer not
            # in options), so both the "stored" and "dropped" paths get exercised
            # against the real DB. The judge call gets a generic "all good" verdict —
            # judge behavior itself is covered by the unit tests.
            async def fake_chat_complete(system_msg, user_msg, config):
                if system_msg == PROMPT_4_SYSTEM:
                    return {
                        "verdicts": [
                            {
                                "index": 0,
                                "requires_computation": False,
                                "derived_answers": ["Ownership rules"],
                                "bloom_aligned": True,
                                "concept_relevant": True,
                                "notes": "",
                            }
                        ]
                    }
                assert system_msg == PROMPT_3_SYSTEM
                return {
                    "questions": [
                        _draft(),
                        _draft(
                            question_text="Does Rust use a garbage collector?",
                            question_type="TrueFalse",
                            options=["True", "False"],
                            correct_answers=["Nope"],  # not in options -> Failed
                            explanation="Rust does not use a garbage collector.",
                        ),
                    ]
                }

            async def fake_embed(texts: list[str]) -> list[list[float]]:
                return [[1.0 if j == i else 0.0 for j in range(1024)] for i in range(len(texts))]

            monkeypatch.setattr(
                "question_generation_service.clients.mistral_client.chat_complete",
                fake_chat_complete,
            )
            monkeypatch.setattr(
                "question_generation_service.clients.mistral_client.embed", fake_embed
            )

            request = QuestionGenerationRequest(
                concept_id=concept_id,
                concept_name="Borrow checker",
                learning_goal="Explain how the borrow checker enforces ownership",
                bloom_level="Understanding",
                difficulty_tier="medium",
            )

            result = await service.generate_batch(request, user_id)

            assert len(result.questions) == 1
            assert result.questions[0].validation_status == "Passed"

            stored_rows = (
                await session.execute(
                    text(
                        "SELECT id, concept_id, bloom_level, difficulty_tier, question_type, "
                        "question_text, options, correct_answers, estimated_time, tags "
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
            assert row.correct_answers == ["Ownership rules"]
            assert row.estimated_time == "30"
            assert row.tags == ["rust"]

            validation_rows = (
                await session.execute(
                    text(
                        "SELECT question_id, validation_status, failed_checks, validation_score "
                        "FROM question_validation_log "
                        "WHERE question_id = :question_id "
                        "OR (question_id IS NULL AND notes LIKE :notes)"
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
        finally:
            # questions/concept_progress_tracker cascade off learning_units, but
            # question_validation_log's "Failed" rows (question_id NULL, no FK
            # to anything) don't — without this, a prior run's leftover NULL-
            # question_id row for this exact draft text corrupts the
            # `OR (question_id IS NULL AND notes LIKE ...)` match above.
            await session.execute(
                text(
                    "DELETE FROM question_validation_log WHERE question_id IS NULL "
                    "AND notes LIKE 'Does Rust use a garbage collector%'"
                )
            )
            await session.execute(
                text("DELETE FROM learning_units WHERE id = :id"), {"id": str(concept_id)}
            )
            await session.execute(
                text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)}
            )
            await session.commit()

    await engine.dispose()
