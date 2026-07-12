"""Exercises the real Step 5 exposure check + Step 7 BKT init flow against a
real Postgres instance (see README.md "Testing" for how to point DATABASE_URL
at a migrated+seeded memosphere_test database). The only mocked piece is the
Mistral call — everything downstream (repositories, DB writes) is real.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from memosphere_domain import EXPOSURE_TO_P_L0
from question_generation_service.core.config import get_settings
from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressInput,
    ConceptProgressRepository,
)
from question_generation_service.repositories.exposure_repository import ExposureRepository
from question_generation_service.repositories.learning_unit_repository import (
    LearningUnitRepository,
)
from question_generation_service.repositories.thema_repository import ThemaRepository
from question_generation_service.schemas.exposure import ExposureRequest
from question_generation_service.schemas.thema import ConfirmRequest, ThemaRequest
from question_generation_service.services.bkt_init_service import BktInitService
from question_generation_service.services.concept_service import ConceptService
from question_generation_service.services.exposure_service import ExposureService
from question_generation_service.services.thema_service import ThemaService

pytestmark = pytest.mark.asyncio


def _thema_extraction_response(thema: str, domain: str, topics: list[str]) -> dict[str, object]:
    return {
        "thema": thema,
        "domain": domain,
        "disambiguator": f"{thema} sense",
        "confirmation": f"You'll be quizzed on {thema}.",
        "topics": topics,
        "confidence": 0.95,
        "alternates": [],
        "input_kind": "topic",
        "reply": "",
    }


def _concept_map_response(concepts: list[dict[str, object]]) -> dict[str, object]:
    return {"concepts": concepts}


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


SCENARIOS = [
    {
        "name": "rust-ownership (unknown exposure -> Practiced)",
        "raw_input": "rust ownership and borrowing",
        "thema": "Rust Ownership",
        "domain": "Software",
        "topics": ["Ownership", "Borrowing"],
        "concepts": [
            {
                "topic": "Ownership",
                "concept": "Move semantics",
                "learning_goal": "Understand moves",
                "bloom_levels": ["Remembering", "Understanding"],
                "estimated_time_minutes": 10,
                "complexity_level": "Medium",
            },
            {
                "topic": "Borrowing",
                "concept": "Borrow checker",
                "learning_goal": "Understand the borrow checker",
                "bloom_levels": ["Applying"],
                "estimated_time_minutes": 15,
                "complexity_level": "High",
            },
        ],
        "pre_existing_exposure": None,
        "answer_exposure": "Practiced",
    },
    {
        "name": "photosynthesis (exposure already on file -> Mastered)",
        "raw_input": "how plants make food from sunlight",
        "thema": "Photosynthesis",
        "domain": "Science",
        "topics": ["Light Reactions", "Calvin Cycle"],
        "concepts": [
            {
                "topic": "Light Reactions",
                "concept": "Photolysis",
                "learning_goal": "Understand photolysis",
                "bloom_levels": ["Remembering", "Applying", "Evaluating"],
                "estimated_time_minutes": 20,
                "complexity_level": "Low",
            },
        ],
        "pre_existing_exposure": "Mastered",
        "answer_exposure": None,
    },
    {
        "name": "docker-containers (unknown exposure -> Unseen)",
        "raw_input": "docker containers and images",
        "thema": "Docker Containers",
        "domain": "Software",
        "topics": ["Images", "Containers", "Volumes"],
        "concepts": [
            {
                "topic": "Images",
                "concept": "Image layering",
                "learning_goal": "Understand image layers",
                "bloom_levels": ["Understanding", "Creating"],
                "estimated_time_minutes": 12,
                "complexity_level": "Medium",
            },
            {
                "topic": "Volumes",
                "concept": "Persistent storage",
                "learning_goal": "Understand volumes",
                "bloom_levels": ["Applying"],
                "estimated_time_minutes": 8,
                "complexity_level": "Low",
            },
        ],
        "pre_existing_exposure": None,
        "answer_exposure": "Unseen",
    },
]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=[s["name"] for s in SCENARIOS])
async def test_exposure_and_bkt_init_fill_tables_correctly(monkeypatch, scenario):
    # A fresh engine per test, not the app's module-level singleton: pytest-asyncio
    # gives each parametrized case its own event loop, and an asyncpg pool created
    # under one loop can't be reused from another.
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        user_id = uuid.uuid4()
        await _insert_user(session, user_id)
        try:
            thema_repository = ThemaRepository(session)
            learning_unit_repository = LearningUnitRepository(session)
            exposure_repository = ExposureRepository(session)
            concept_progress_repository = ConceptProgressRepository(session)
            concept_service = ConceptService(learning_unit_repository)
            bkt_init_service = BktInitService(concept_progress_repository)
            thema_service = ThemaService(
                thema_repository, concept_service, exposure_repository, bkt_init_service
            )
            exposure_service = ExposureService(
                thema_repository, exposure_repository, learning_unit_repository, bkt_init_service
            )

            async def fake_thema_chat_complete(system_msg, user_msg, config):
                return _thema_extraction_response(
                    scenario["thema"], scenario["domain"], scenario["topics"]
                )

            async def fake_concept_chat_complete(system_msg, user_msg, config):
                return _concept_map_response(scenario["concepts"])

            async def fake_embed(texts: list[str]) -> list[list[float]]:
                return [[1.0 if j == i else 0.0 for j in range(1024)] for i in range(len(texts))]

            monkeypatch.setattr(
                "question_generation_service.services.thema_service.chat_complete",
                fake_thema_chat_complete,
            )
            monkeypatch.setattr(
                "question_generation_service.services.concept_service.chat_complete",
                fake_concept_chat_complete,
            )
            monkeypatch.setattr(
                "question_generation_service.clients.mistral_client.embed", fake_embed
            )

            if scenario["pre_existing_exposure"] is not None:
                await exposure_repository.save(
                    user_id,
                    scenario["thema"],
                    scenario["pre_existing_exposure"],
                    source="test_seed",
                )

            extraction_result = await thema_service.extract(
                ThemaRequest(raw_user_input=scenario["raw_input"])
            )
            assert extraction_result.status == "resolved"

            confirmed = await thema_service.confirm(
                extraction_result.extraction_id, ConfirmRequest(), user_id
            )
            assert confirmed.thema == scenario["thema"]

            expected_level = scenario["pre_existing_exposure"] or scenario["answer_exposure"]
            assert confirmed.exposure_required == (scenario["pre_existing_exposure"] is None)

            if scenario["answer_exposure"] is not None:
                exposure_result = await exposure_service.submit(
                    extraction_result.extraction_id,
                    user_id,
                    ExposureRequest(exposure_level=scenario["answer_exposure"]),
                )
                assert exposure_result.exposure_level == scenario["answer_exposure"]

            # --- verify learning_units got the concepts from Step 6 ---
            learning_units = (
                await session.execute(
                    text(
                        "SELECT id, concept_name, bloom_levels_supported FROM learning_units "
                        "WHERE thema = :thema"
                    ),
                    {"thema": scenario["thema"]},
                )
            ).all()
            assert len(learning_units) == len(scenario["concepts"])
            expected_concept_names = {c["concept"] for c in scenario["concepts"]}
            assert {row.concept_name for row in learning_units} == expected_concept_names

            # --- verify user_thema_exposure (Step 5) ---
            exposure_row = (
                await session.execute(
                    text(
                        "SELECT exposure_level FROM user_thema_exposure "
                        "WHERE user_id = :user_id AND thema = :thema"
                    ),
                    {"user_id": str(user_id), "thema": scenario["thema"]},
                )
            ).one()
            assert exposure_row.exposure_level == expected_level

            # --- verify concept_progress_tracker (Step 7 BKT init) ---
            expected_p_l0 = EXPOSURE_TO_P_L0[expected_level]
            expected_pair_count = sum(len(c["bloom_levels"]) for c in scenario["concepts"])
            progress_rows = (
                await session.execute(
                    text(
                        "SELECT concept_id, bloom_level, p_ln, attempt_count, mastery_status "
                        "FROM concept_progress_tracker WHERE user_id = :user_id"
                    ),
                    {"user_id": str(user_id)},
                )
            ).all()
            assert len(progress_rows) == expected_pair_count
            for row in progress_rows:
                # p_ln is stored as Postgres `real` (single precision) — compare with
                # tolerance rather than exact equality.
                assert row.p_ln == pytest.approx(expected_p_l0)
                assert row.attempt_count == 0
                assert row.mastery_status == "In Progress"

            concept_ids = {row.id for row in learning_units}
            assert {row.concept_id for row in progress_rows} == concept_ids
        finally:
            # thema_extraction_inputs/user_thema_exposure/concept_progress_tracker
            # all cascade off users/learning_units. Scenarios use fixed thema
            # names (parametrize ids double as documentation), so a prior run's
            # leftover rows would otherwise corrupt this run's own count
            # assertions above (accumulating duplicate learning_units per thema).
            await session.execute(
                text("DELETE FROM learning_units WHERE thema = :thema"),
                {"thema": scenario["thema"]},
            )
            await session.execute(
                text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)}
            )
            await session.commit()

    await engine.dispose()


async def test_bkt_init_is_idempotent_on_repeat_confirm():
    """Reproduces the production crash: a learner re-confirms a thema whose
    concepts are already tracked for them (dedup means the same concept_ids
    come back). Before the ON CONFLICT DO NOTHING fix, the second
    initialize_batch call raised UniqueViolationError on the
    (user_id, concept_id, bloom_level) primary key instead of no-op'ing.
    """
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    async with session_factory() as session:
        user_id = uuid.uuid4()
        concept_id = uuid.uuid4()
        await _insert_user(session, user_id)
        await _insert_learning_unit(session, concept_id, "Idempotency Check")

        concept_progress_repository = ConceptProgressRepository(session)
        rows: list[ConceptProgressInput] = [
            {"concept_id": concept_id, "bloom_level": "Remembering", "p_ln": 0.2},
            {"concept_id": concept_id, "bloom_level": "Understanding", "p_ln": 0.2},
        ]

        first = await concept_progress_repository.initialize_batch(user_id, rows)
        assert len(first) == 2

        # The exact scenario that crashed in production: re-confirming the
        # same thema seeds the same (user, concept, bloom) pairs again.
        second = await concept_progress_repository.initialize_batch(user_id, rows)
        assert second == []

        remaining = (
            await session.execute(
                text("SELECT COUNT(*) FROM concept_progress_tracker WHERE user_id = :user_id"),
                {"user_id": str(user_id)},
            )
        ).scalar_one()
        assert remaining == 2

        # learning_units cascades to concept_progress_tracker.
        await session.execute(
            text("DELETE FROM learning_units WHERE id = :id"), {"id": str(concept_id)}
        )
        await session.execute(text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)})
        await session.commit()

    await engine.dispose()
