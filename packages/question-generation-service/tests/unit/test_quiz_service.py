from dataclasses import dataclass, field
from uuid import UUID, uuid4

import pytest

from question_generation_service.core.exceptions import NotFoundError
from question_generation_service.repositories.quiz_repository import (
    OutboxInput,
    QuizEntryProtocol,
    QuizInput,
)
from question_generation_service.schemas.quiz import QuizCreateRequest
from question_generation_service.services.quiz_service import (
    JOBS_GENERATE_QUESTIONS,
    QuizService,
)

pytestmark = pytest.mark.asyncio


@dataclass
class FakeUnit:
    id: UUID
    thema: str
    concept_name: str
    learning_goal: str | None
    bloom_levels_supported: list[str] | None
    topic: str | None = "Topic"
    estimated_time_minutes: int | None = 10
    bloom_coverage_score: int | None = 3
    complexity_level: str | None = "Medium"


@dataclass
class FakeQuiz:
    id: UUID
    owner_user_id: UUID
    thema: str
    title: str
    question_types: list[str]
    question_count: int | None
    time_limit_minutes: int | None
    visibility: str


@dataclass
class FakeQuizRepository:
    created: list[tuple[QuizInput, list[OutboxInput]]] = field(default_factory=list)

    async def create_with_outbox(
        self, quiz: QuizInput, outbox_entries: list[OutboxInput]
    ) -> QuizEntryProtocol:
        self.created.append((quiz, outbox_entries))
        return FakeQuiz(id=uuid4(), **quiz)


class FakeLearningUnitRepository:
    def __init__(self, units: list[FakeUnit]):
        self.units = units

    async def save_batch(self, thema: str, concepts: list) -> list[FakeUnit]:  # pragma: no cover
        raise NotImplementedError

    async def get_by_thema(self, thema: str) -> list[FakeUnit]:
        return [u for u in self.units if u.thema == thema]


def make_units(thema: str, count: int, blooms: list[str]) -> list[FakeUnit]:
    return [
        FakeUnit(
            id=uuid4(),
            thema=thema,
            concept_name=f"Concept {i}",
            learning_goal=f"Goal {i}",
            bloom_levels_supported=blooms,
        )
        for i in range(count)
    ]


def make_service(units: list[FakeUnit]) -> tuple[QuizService, FakeQuizRepository]:
    quiz_repository = FakeQuizRepository()
    return QuizService(quiz_repository, FakeLearningUnitRepository(units)), quiz_repository


async def test_unknown_thema_raises_not_found():
    service, _ = make_service([])
    with pytest.raises(NotFoundError, match="confirm the thema first"):
        await service.create(
            uuid4(), QuizCreateRequest(thema="Ghosts", question_types=["MCQ"], question_count=5)
        )


async def test_enqueues_one_job_per_batch_of_five():
    units = make_units("Photosynthesis", 4, ["Remembering", "Understanding"])
    service, repository = make_service(units)

    response = await service.create(
        uuid4(),
        QuizCreateRequest(thema="Photosynthesis", question_types=["MCQ"], question_count=12),
    )

    # ceil(12 / 5) = 3 buckets out of the 8 available concept-Bloom pairs.
    assert response.generation_batches_enqueued == 3
    _, outbox_entries = repository.created[0]
    assert len(outbox_entries) == 3
    assert all(e["topic"] == JOBS_GENERATE_QUESTIONS for e in outbox_entries)


async def test_buckets_capped_by_available_pairs():
    units = make_units("Tiny", 1, ["Remembering"])  # a single pair exists
    service, repository = make_service(units)

    response = await service.create(
        uuid4(), QuizCreateRequest(thema="Tiny", question_types=["MCQ"], question_count=50)
    )

    assert response.generation_batches_enqueued == 1
    assert len(repository.created[0][1]) == 1


async def test_time_based_sizing_uses_45s_per_question():
    units = make_units("Chrono", 5, ["Remembering", "Understanding"])
    service, repository = make_service(units)

    response = await service.create(
        uuid4(), QuizCreateRequest(thema="Chrono", question_types=["MCQ"], time_limit_minutes=15)
    )

    # 15 min → 20 questions → 4 batches.
    assert response.generation_batches_enqueued == 4
    assert len(repository.created[0][1]) == 4


async def test_job_payload_carries_the_full_generation_request():
    owner = uuid4()
    units = make_units("Photosynthesis", 1, ["Applying"])
    service, repository = make_service(units)

    await service.create(
        owner,
        QuizCreateRequest(
            thema="Photosynthesis",
            question_types=["MCQ", "TrueFalse"],
            question_count=5,
        ),
    )

    payload = repository.created[0][1][0]["payload"]
    assert payload == {
        "owner_user_id": str(owner),
        "concept_id": str(units[0].id),
        "concept_name": "Concept 0",
        "learning_goal": "Goal 0",
        "bloom_level": "Applying",
        "difficulty_tier": "medium",
        "allowed_question_types": ["MCQ", "TrueFalse"],
    }


async def test_null_learning_goal_and_blooms_are_tolerated():
    unit = FakeUnit(
        id=uuid4(),
        thema="Sparse",
        concept_name="Bare Concept",
        learning_goal=None,
        bloom_levels_supported=None,
    )
    rich = make_units("Sparse", 1, ["Remembering"])[0]
    rich.learning_goal = None
    service, repository = make_service([unit, rich])

    response = await service.create(
        uuid4(), QuizCreateRequest(thema="Sparse", question_types=["MCQ"], question_count=5)
    )

    # The bloom-less unit contributes no bucket; the goal-less one gets a fallback.
    assert response.generation_batches_enqueued == 1
    payload = repository.created[0][1][0]["payload"]
    assert payload["learning_goal"] == "Understand Concept 0"


async def test_quiz_row_defaults_title_to_thema_and_keeps_config():
    owner = uuid4()
    service, repository = make_service(make_units("Photosynthesis", 1, ["Remembering"]))

    response = await service.create(
        owner,
        QuizCreateRequest(
            thema="Photosynthesis",
            question_types=["FillInBlank"],
            question_count=5,
            visibility="shared",
        ),
    )

    quiz_input, _ = repository.created[0]
    assert quiz_input["title"] == "Photosynthesis"
    assert quiz_input["owner_user_id"] == owner
    assert quiz_input["visibility"] == "shared"
    assert response.title == "Photosynthesis"
    assert response.question_types == ["FillInBlank"]
    assert response.visibility == "shared"


def test_request_requires_some_size():
    with pytest.raises(ValueError, match="question_count or time_limit_minutes"):
        QuizCreateRequest(thema="X", question_types=["MCQ"])
