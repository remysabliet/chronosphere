"""Exercises ConceptProgressRepository directly against real Postgres — the
persistence layer MasteryService.record_attempt writes through (see
test_mastery_service.py for the pure-function/service-level coverage above
this, and test_session_flow_integration.py for the full HTTP-to-DB path that
sits on top of it).
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from question_generation_service.core.config import get_settings
from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressInput,
    ConceptProgressRepository,
)

pytestmark = pytest.mark.asyncio


async def _insert_user(session, user_id: uuid.UUID) -> None:
    await session.execute(
        text(
            "INSERT INTO users (user_id, name, email, created_at) "
            "VALUES (:user_id, 'Test User', :email, now())"
        ),
        {"user_id": str(user_id), "email": f"{user_id}@example.com"},
    )


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
            "topic": "Topic",
            "concept_name": "Concept",
            "complexity_level": "Medium",
        },
    )


def _engine_and_session_factory():
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    return engine, async_sessionmaker(bind=engine, expire_on_commit=False)


async def test_initialize_batch_then_get_round_trips_p_ln():
    engine, session_factory = _engine_and_session_factory()

    async with session_factory() as session:
        user_id, concept_id = uuid.uuid4(), uuid.uuid4()
        await _insert_user(session, user_id)
        await _insert_learning_unit(session, concept_id, "Repo Test Round Trip")
        await session.commit()

        repository = ConceptProgressRepository(session)
        try:
            await repository.initialize_batch(
                user_id,
                [ConceptProgressInput(concept_id=concept_id, bloom_level="Remembering", p_ln=0.2)],
            )

            fetched = await repository.get(user_id, concept_id, "Remembering")

            assert fetched is not None
            assert fetched.p_ln == pytest.approx(0.2)
            assert fetched.mastery_status == "In Progress"
        finally:
            await session.execute(
                text("DELETE FROM learning_units WHERE id = :id"), {"id": str(concept_id)}
            )
            await session.execute(
                text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)}
            )
            await session.commit()

    await engine.dispose()


async def test_get_returns_none_when_no_bkt_state_seeded():
    engine, session_factory = _engine_and_session_factory()

    async with session_factory() as session:
        repository = ConceptProgressRepository(session)

        fetched = await repository.get(uuid.uuid4(), uuid.uuid4(), "Remembering")

        assert fetched is None

    await engine.dispose()


async def test_record_attempt_persists_new_p_ln_and_mastery_status():
    engine, session_factory = _engine_and_session_factory()

    async with session_factory() as session:
        user_id, concept_id = uuid.uuid4(), uuid.uuid4()
        await _insert_user(session, user_id)
        await _insert_learning_unit(session, concept_id, "Repo Test Record Attempt")
        await session.commit()

        repository = ConceptProgressRepository(session)
        try:
            await repository.initialize_batch(
                user_id,
                [ConceptProgressInput(concept_id=concept_id, bloom_level="Remembering", p_ln=0.2)],
            )

            await repository.record_attempt(
                user_id,
                concept_id,
                "Remembering",
                p_ln=0.9,
                is_correct=True,
                mastery_status="Mastered",
            )

            row = (
                await session.execute(
                    text(
                        "SELECT p_ln, mastery_status, attempt_count, correct_count, slip_count "
                        "FROM concept_progress_tracker "
                        "WHERE user_id = :user_id AND concept_id = :concept_id AND bloom_level = 'Remembering'"
                    ),
                    {"user_id": str(user_id), "concept_id": str(concept_id)},
                )
            ).one()
            assert row.p_ln == pytest.approx(0.9)
            assert row.mastery_status == "Mastered"
            assert row.attempt_count == 1
            assert row.correct_count == 1
            assert row.slip_count == 0
        finally:
            await session.execute(
                text("DELETE FROM learning_units WHERE id = :id"), {"id": str(concept_id)}
            )
            await session.execute(
                text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)}
            )
            await session.commit()

    await engine.dispose()


async def test_record_attempt_tracks_correct_and_slip_counts_across_multiple_attempts():
    engine, session_factory = _engine_and_session_factory()

    async with session_factory() as session:
        user_id, concept_id = uuid.uuid4(), uuid.uuid4()
        await _insert_user(session, user_id)
        await _insert_learning_unit(session, concept_id, "Repo Test Counts")
        await session.commit()

        repository = ConceptProgressRepository(session)
        try:
            await repository.initialize_batch(
                user_id,
                [ConceptProgressInput(concept_id=concept_id, bloom_level="Remembering", p_ln=0.2)],
            )

            await repository.record_attempt(
                user_id,
                concept_id,
                "Remembering",
                p_ln=0.3,
                is_correct=False,
                mastery_status="In Progress",
            )
            await repository.record_attempt(
                user_id,
                concept_id,
                "Remembering",
                p_ln=0.5,
                is_correct=True,
                mastery_status="In Progress",
            )
            await repository.record_attempt(
                user_id,
                concept_id,
                "Remembering",
                p_ln=0.6,
                is_correct=True,
                mastery_status="In Progress",
            )

            row = (
                await session.execute(
                    text(
                        "SELECT p_ln, attempt_count, correct_count, slip_count, first_attempt, last_attempt "
                        "FROM concept_progress_tracker "
                        "WHERE user_id = :user_id AND concept_id = :concept_id AND bloom_level = 'Remembering'"
                    ),
                    {"user_id": str(user_id), "concept_id": str(concept_id)},
                )
            ).one()
            assert row.p_ln == pytest.approx(0.6)
            assert row.attempt_count == 3
            assert row.correct_count == 2
            assert row.slip_count == 1
            # first_attempt is stamped once (COALESCE) and never overwritten;
            # last_attempt keeps moving forward with every call.
            assert row.first_attempt is not None
            assert row.last_attempt is not None
            assert row.first_attempt <= row.last_attempt
        finally:
            await session.execute(
                text("DELETE FROM learning_units WHERE id = :id"), {"id": str(concept_id)}
            )
            await session.execute(
                text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)}
            )
            await session.commit()

    await engine.dispose()


async def test_initialize_batch_is_a_noop_for_already_tracked_pairs():
    engine, session_factory = _engine_and_session_factory()

    async with session_factory() as session:
        user_id, concept_id = uuid.uuid4(), uuid.uuid4()
        await _insert_user(session, user_id)
        await _insert_learning_unit(session, concept_id, "Repo Test Dedup")
        await session.commit()

        repository = ConceptProgressRepository(session)
        try:
            row: ConceptProgressInput = {
                "concept_id": concept_id,
                "bloom_level": "Remembering",
                "p_ln": 0.2,
            }
            await repository.initialize_batch(user_id, [row])
            # Real progress has since been recorded — a second confirm of the
            # same thema must not reset it back to P(L0).
            await repository.record_attempt(
                user_id,
                concept_id,
                "Remembering",
                p_ln=0.7,
                is_correct=True,
                mastery_status="In Progress",
            )

            await repository.initialize_batch(user_id, [row])

            fetched = await repository.get(user_id, concept_id, "Remembering")
            assert fetched is not None
            assert fetched.p_ln == pytest.approx(0.7)
        finally:
            await session.execute(
                text("DELETE FROM learning_units WHERE id = :id"), {"id": str(concept_id)}
            )
            await session.execute(
                text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)}
            )
            await session.commit()

    await engine.dispose()
