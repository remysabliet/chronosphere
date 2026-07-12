"""Exercises the pool-reuse repository methods (get_by_concept_bloom_difficulty,
get_served_question_ids, mark_served) against a real Postgres instance — the
ON CONFLICT upsert semantics in mark_served specifically need a real DB to
verify, not a fake.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from question_generation_service.core.config import get_settings
from question_generation_service.repositories.question_repository import (
    QuestionInput,
    QuestionRepository,
)

pytestmark = pytest.mark.asyncio


async def _insert_user(session, user_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (:user_id, :name, :email, now())"
        ),
        {
            "user_id": str(user_id),
            "name": "Pool Reuse Test User",
            "email": f"{user_id}@example.com",
        },
    )
    await session.commit()


async def _insert_learning_unit(session, concept_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO learning_units "
            "(id, thema, topic, concept_name, complexity_level, created_at) "
            "VALUES (:id, 'Pool Reuse Thema', 'Topic', 'Concept', 'Medium', now())"
        ),
        {"id": str(concept_id)},
    )
    await session.commit()


def _question_input(concept_id: uuid.UUID, question_text: str) -> QuestionInput:
    return QuestionInput(
        concept_id=concept_id,
        bloom_level="Understanding",
        difficulty_tier="medium",
        question_type="MCQ",
        question_text=question_text,
        options=["A", "B", "C", "D"],
        correct_answers=["A"],
        explanation="Because A is correct.",
        estimated_time="30",
        tags=[],
        embedding=[0.0] * 1024,
    )


async def test_pool_reuse_repository_methods_against_real_db():
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        user_id = uuid.uuid4()
        concept_id = uuid.uuid4()
        await _insert_user(session, user_id)
        await _insert_learning_unit(session, concept_id)

        repository = QuestionRepository(session)
        stored = await repository.save_batch(
            [
                _question_input(concept_id, "Q1"),
                _question_input(concept_id, "Q2"),
                _question_input(concept_id, "Q3"),
            ]
        )
        question_ids = [q.id for q in stored]

        # A different (bloom_level, difficulty_tier) cell must not see these.
        other_cell = await repository.get_by_concept_bloom_difficulty(
            concept_id, "Remembering", "medium"
        )
        assert other_cell == []

        pool = await repository.get_by_concept_bloom_difficulty(
            concept_id, "Understanding", "medium"
        )
        assert {q.id for q in pool} == set(question_ids)

        # Nothing served yet.
        served = await repository.get_served_question_ids(user_id, question_ids)
        assert served == set()

        # Serve two of the three, verify the upsert path doesn't error on repeat.
        await repository.mark_served(user_id, question_ids[:2])
        await repository.mark_served(user_id, question_ids[:2])

        served = await repository.get_served_question_ids(user_id, question_ids)
        assert served == set(question_ids[:2])

        # A different user has an independent serving history.
        other_user_id = uuid.uuid4()
        await _insert_user(session, other_user_id)
        served_for_other = await repository.get_served_question_ids(other_user_id, question_ids)
        assert served_for_other == set()

        await session.execute(
            text("DELETE FROM learning_units WHERE id = :id"), {"id": str(concept_id)}
        )
        await session.execute(text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)})
        await session.execute(
            text("DELETE FROM users WHERE user_id = :id"), {"id": str(other_user_id)}
        )
        await session.commit()

    await engine.dispose()
