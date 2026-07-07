"""Live end-to-end test against the REAL Mistral API and a real Postgres DB.

Exercises the full main-workflow.md pipeline exactly as it's actually wired up:
Prompt 1 (thema extraction) -> Prompt 2 (concept mapping, with dedup) ->
exposure check -> BKT init (Step 7) -> Prompt 3 (question generation) ->
Prompt 4 (judge, independent re-derivation) -> Step 8A validation.

Not part of the default test run — it costs real API credits and needs a
real MISTRAL_API_KEY (not the .env.example placeholder). Run it explicitly:

    RUN_LIVE_MISTRAL_TESTS=1 DATABASE_URL="postgresql://memosphere:memosphere_secure_dev_2025!@localhost:5432/memosphere_test" \\
        uv run pytest tests/integration/test_live_ai_pipeline.py -v -s

The -s is required to see the printed questions — reading and judging actual
generated content is the point of this test; no automated check replaces
that. Runs deliberately slow (a short sleep between calls) since Mistral's
rate limit is tight enough to trip within a single run otherwise.

Override the topic with LIVE_AI_TEST_INPUT=... if you want to try something
else; keep MAX_QUESTION_BATCHES small if you do, for the same rate-limit reason.
"""

import asyncio
import os
import uuid
from typing import cast

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from memosphere_domain import BloomLevel
from question_generation_service.core.config import get_settings
from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressRepository,
)
from question_generation_service.repositories.exposure_repository import ExposureRepository
from question_generation_service.repositories.learning_unit_repository import (
    LearningUnitRepository,
)
from question_generation_service.repositories.question_repository import QuestionRepository
from question_generation_service.repositories.thema_repository import ThemaRepository
from question_generation_service.schemas.exposure import ExposureRequest
from question_generation_service.schemas.question import QuestionGenerationRequest, StoredQuestion
from question_generation_service.schemas.thema import ConfirmRequest, ThemaRequest
from question_generation_service.services.bkt_init_service import BktInitService
from question_generation_service.services.concept_service import ConceptService
from question_generation_service.services.exposure_service import ExposureService
from question_generation_service.services.question_service import QuestionService
from question_generation_service.services.thema_service import ThemaService

RAW_INPUT = os.environ.get("LIVE_AI_TEST_INPUT", "the doppler effect in physics")
EXPOSURE_LEVEL = "Recognized"
# Small on purpose: enough to sanity-check the pipeline and read real output,
# not enough to trip Mistral's rate limit or run up a real bill every run.
MAX_QUESTION_BATCHES = 2
CALL_SPACING_SECONDS = 5

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(
        os.environ.get("RUN_LIVE_MISTRAL_TESTS") != "1",
        reason=(
            "Hits the real Mistral API and costs real credits — opt in explicitly "
            "with RUN_LIVE_MISTRAL_TESTS=1 (see this file's module docstring for "
            "the full command)."
        ),
    ),
]


def _print_question(q: StoredQuestion) -> None:
    print(f"\n  [{q.validation_status}] ({q.question_type}) {q.question_text}")
    print(f"    options: {q.options}")
    print(f"    correct_answers: {q.correct_answers!r}")
    print(f"    explanation: {q.explanation}")
    print(f"    tags: {q.tags}")


async def test_live_pipeline_produces_readable_questions():
    settings = get_settings()
    assert "your_dev_mistral_api_key_here" not in settings.MISTRAL_API_KEY, (
        "MISTRAL_API_KEY is still the .env.example placeholder — set a real key "
        "in .env to run this test."
    )

    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        user_id = uuid.uuid4()
        extraction_id: uuid.UUID | None = None
        thema: str | None = None

        try:
            await session.execute(
                text(
                    "INSERT INTO users (user_id, name, email, created_at) "
                    "VALUES (:id, 'Live AI Test User', :email, now())"
                ),
                {"id": str(user_id), "email": f"{user_id}@example.com"},
            )
            await session.commit()

            thema_repo = ThemaRepository(session)
            learning_unit_repo = LearningUnitRepository(session)
            exposure_repo = ExposureRepository(session)
            concept_progress_repo = ConceptProgressRepository(session)
            question_repo = QuestionRepository(session)

            concept_service = ConceptService(learning_unit_repo)
            bkt_init_service = BktInitService(concept_progress_repo)
            thema_service = ThemaService(
                thema_repo, concept_service, exposure_repo, bkt_init_service
            )
            exposure_service = ExposureService(
                thema_repo, exposure_repo, learning_unit_repo, bkt_init_service
            )
            question_service = QuestionService(question_repo)

            print(f"\n=== Prompt 1: extract({RAW_INPUT!r}) ===")
            extraction = await thema_service.extract(ThemaRequest(raw_user_input=RAW_INPUT))
            extraction_id = extraction.extraction_id
            print(extraction)
            assert extraction.status == "resolved", (
                f"Expected a resolved thema for this input, got status={extraction.status!r} "
                "— pick a clearer LIVE_AI_TEST_INPUT."
            )
            await asyncio.sleep(CALL_SPACING_SECONDS)

            print("\n=== confirm() -> Prompt 2 (concept mapping) + exposure check ===")
            confirmed = await thema_service.confirm(
                extraction.extraction_id, ConfirmRequest(), user_id
            )
            thema = confirmed.thema
            print(f"thema={confirmed.thema!r} topics={confirmed.topics}")

            concepts = await learning_unit_repo.get_by_thema(confirmed.thema)
            assert len(concepts) > 0, "Prompt 2 produced no concepts"
            print(f"\n{len(concepts)} concept(s) mapped:")
            for c in concepts:
                print(
                    f"  - [{c.complexity_level}] {c.concept_name} "
                    f"(bloom_levels={c.bloom_levels_supported})"
                )

            if confirmed.exposure_required:
                await asyncio.sleep(CALL_SPACING_SECONDS)
                print(f"\n=== submit exposure={EXPOSURE_LEVEL!r} -> BKT init (Step 7) ===")
                exposure_result = await exposure_service.submit(
                    extraction.extraction_id,
                    user_id,
                    ExposureRequest(exposure_level=EXPOSURE_LEVEL),
                )
                print(exposure_result)
                assert exposure_result.concepts_initialized > 0

            print("\n=== Prompt 3 + Prompt 4 (judge): sample question batches ===")
            batches_run = 0
            total_stored = 0
            for concept in concepts:
                if batches_run >= MAX_QUESTION_BATCHES:
                    break
                for bloom_level in concept.bloom_levels_supported or []:
                    if batches_run >= MAX_QUESTION_BATCHES:
                        break
                    await asyncio.sleep(CALL_SPACING_SECONDS)
                    request = QuestionGenerationRequest(
                        concept_id=concept.id,
                        concept_name=concept.concept_name,
                        learning_goal=concept.learning_goal or f"Understand {concept.concept_name}",
                        bloom_level=cast(BloomLevel, bloom_level),
                        difficulty_tier="medium",
                    )
                    print(f"\n--- {concept.concept_name} / {bloom_level} / medium ---")
                    result = await question_service.generate_batch(request, user_id)
                    print(f"{len(result.questions)} question(s) passed validation and were stored:")
                    for q in result.questions:
                        _print_question(q)
                    total_stored += len(result.questions)
                    batches_run += 1

            assert batches_run > 0, "No concept had any Bloom level to generate questions for"
            assert total_stored > 0, (
                "Every generated question was rejected by validation/the judge — "
                "check the printed output above for why."
            )

            log_rows = (
                await session.execute(
                    text(
                        "SELECT validation_status, failed_checks, notes "
                        "FROM question_validation_log ORDER BY timestamp"
                    )
                )
            ).all()
            print(f"\n=== question_validation_log: {len(log_rows)} entries ===")
            for row in log_rows:
                print(f"  {row.validation_status} failed={row.failed_checks} notes={row.notes}")

        finally:
            # learning_units cascades to questions/concept_progress_tracker/
            # question_validation_log; users cascades to user_thema_exposure.
            # Keeps repeated runs from accumulating garbage in the test DB.
            if thema is not None:
                await session.execute(
                    text("DELETE FROM learning_units WHERE thema = :thema"), {"thema": thema}
                )
            if extraction_id is not None:
                await session.execute(
                    text("DELETE FROM thema_extraction_inputs WHERE id = :id"),
                    {"id": str(extraction_id)},
                )
            await session.execute(
                text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)}
            )
            await session.commit()

    await engine.dispose()
