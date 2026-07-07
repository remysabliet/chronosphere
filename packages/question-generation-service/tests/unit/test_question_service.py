from collections.abc import Sequence
from typing import cast
from uuid import UUID, uuid4

import pytest
from mistralai.client.models.jsonschema import JSONSchema

from memosphere_domain import ALL_QUESTION_TYPES
from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.prompts.question_generation import build_prompt_3_system
from question_generation_service.prompts.question_judge import PROMPT_4_SYSTEM
from question_generation_service.repositories.question_repository import (
    QuestionInput,
    ValidationLogInput,
)
from question_generation_service.schemas.question import BATCH_SIZE, QuestionGenerationRequest
from question_generation_service.services.question_service import QuestionService

_UNSET = object()
# Fixed across most tests below — none of them care about per-user pool
# dedup, only the dedicated pool-reuse tests further down do.
_USER_ID = uuid4()

# _request() below never overrides allowed_question_types, so every draft in
# this file is generated under the default (unrestricted) prompt.
PROMPT_3_SYSTEM = build_prompt_3_system(ALL_QUESTION_TYPES)

# Generic enough index range to cover any small test batch — indices beyond
# what a batch actually needs are simply never looked up. derived_answers
# matches _draft()'s default correct_answers so the default case agrees.
_DEFAULT_JUDGE_RESPONSE = {
    "verdicts": [
        {
            "index": i,
            "requires_computation": False,
            "derived_answers": ["Ownership rules"],
            "bloom_aligned": True,
            "concept_relevant": True,
            "notes": "",
        }
        for i in range(10)
    ]
}


class _FakeEntry:
    def __init__(self, entry_id: UUID, question: QuestionInput) -> None:
        self.id = entry_id
        self.concept_id = question["concept_id"]
        self.bloom_level = question["bloom_level"]
        self.difficulty_tier = question["difficulty_tier"]
        # Explicitly widened to match QuestionEntryProtocol's optional fields —
        # pyright treats Protocol data attributes as invariant, so the narrower
        # (non-None) types QuestionInput provides won't structurally match otherwise.
        self.question_type: str | None = question["question_type"]
        self.question_text = question["question_text"]
        self.options = question["options"]
        self.correct_answers: list[str] | None = question["correct_answers"]
        self.explanation: str | None = question["explanation"]
        self.estimated_time: str | None = question["estimated_time"]
        self.tags: list[str] | None = question["tags"]


class FakeQuestionRepository:
    def __init__(self) -> None:
        self.saved_batches: list[list[QuestionInput]] = []
        self.logged: list[list[ValidationLogInput]] = []
        # Pre-existing pool entries, keyed loosely — filtered by attribute in
        # get_by_concept_bloom_difficulty, same as the real WHERE clause.
        self.pool: list[_FakeEntry] = []
        self.served: dict[UUID, set[UUID]] = {}
        self.mark_served_calls: list[tuple[UUID, list[UUID]]] = []

    async def save_batch(self, questions: list[QuestionInput]) -> list[_FakeEntry]:
        self.saved_batches.append(questions)
        return [_FakeEntry(uuid4(), question) for question in questions]

    async def log_validations(self, entries: list[ValidationLogInput]) -> None:
        self.logged.append(entries)

    async def get_by_concept_bloom_difficulty(
        self, concept_id: UUID, bloom_level: str, difficulty_tier: str
    ) -> list[_FakeEntry]:
        return [
            e
            for e in self.pool
            if e.concept_id == concept_id
            and e.bloom_level == bloom_level
            and e.difficulty_tier == difficulty_tier
        ]

    async def get_served_question_ids(
        self, user_id: UUID, question_ids: Sequence[UUID]
    ) -> set[UUID]:
        seen = self.served.get(user_id, set())
        return {qid for qid in question_ids if qid in seen}

    async def mark_served(self, user_id: UUID, question_ids: Sequence[UUID]) -> None:
        self.mark_served_calls.append((user_id, list(question_ids)))
        self.served.setdefault(user_id, set()).update(question_ids)


def _draft(
    question_type: str = "MCQ",
    question_text: str = "What does the borrow checker enforce?",
    options: list[str] | None | object = _UNSET,
    correct_answers: list[str] | None = None,
    explanation: str = "It enforces Rust's ownership and borrowing rules at compile time.",
) -> dict[str, object]:
    # options=None must mean "explicitly no options" (e.g. FillInBlank), distinct
    # from "not specified" (which defaults to the MCQ-style option list below).
    resolved_options = (
        ["Ownership rules", "Garbage collection", "Type inference", "Macros"]
        if options is _UNSET
        else options
    )
    return {
        "question_type": question_type,
        "question_text": question_text,
        "options": resolved_options,
        "correct_answers": correct_answers if correct_answers is not None else ["Ownership rules"],
        "explanation": explanation,
        "estimated_time_seconds": 30,
        "tags": ["rust"],
    }


def _pool_entry(
    concept_id: UUID,
    bloom_level: str = "Understanding",
    difficulty_tier: str = "medium",
    question_text: str = "Pool question",
    entry_id: UUID | None = None,
) -> _FakeEntry:
    question: QuestionInput = {
        "concept_id": concept_id,
        "bloom_level": bloom_level,
        "difficulty_tier": difficulty_tier,
        "question_type": "MCQ",
        "question_text": question_text,
        "options": ["A", "B", "C", "D"],
        "correct_answers": ["A"],
        "explanation": "Because A is correct, per the pool fixture.",
        "estimated_time": "30",
        "tags": [],
    }
    return _FakeEntry(entry_id if entry_id is not None else uuid4(), question)


def _request() -> QuestionGenerationRequest:
    return QuestionGenerationRequest(
        concept_id=uuid4(),
        concept_name="Borrow checker",
        learning_goal="Explain how the borrow checker enforces ownership",
        bloom_level="Understanding",
        difficulty_tier="medium",
    )


def _patch_chat_complete(
    monkeypatch,
    generation_response: dict[str, object],
    judge_response: dict[str, object] | None = None,
) -> list[str]:
    calls: list[str] = []

    async def fake(system_msg, user_msg, config):
        calls.append(system_msg)
        if system_msg == PROMPT_4_SYSTEM:
            return judge_response if judge_response is not None else _DEFAULT_JUDGE_RESPONSE
        assert system_msg == PROMPT_3_SYSTEM
        return generation_response

    monkeypatch.setattr("question_generation_service.services.question_service.chat_complete", fake)
    return calls


@pytest.mark.asyncio
async def test_stores_only_passed_and_warning_questions(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {
            "questions": [
                _draft(),  # Passed
                _draft(question_text=""),  # Failed — empty stem
            ]
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert len(result.questions) == 1
    assert result.questions[0].validation_status == "Passed"
    assert len(repository.saved_batches) == 1
    assert len(repository.saved_batches[0]) == 1


@pytest.mark.asyncio
async def test_logs_validation_for_every_draft_including_failed(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {
            "questions": [
                _draft(),
                _draft(question_text=""),
            ]
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    await service.generate_batch(_request(), _USER_ID)

    assert len(repository.logged) == 1
    logged_entries = repository.logged[0]
    assert len(logged_entries) == 2
    statuses = {entry["validation_status"] for entry in logged_entries}
    assert statuses == {"Passed", "Failed"}
    failed_entry = next(e for e in logged_entries if e["validation_status"] == "Failed")
    assert failed_entry["question_id"] is None


@pytest.mark.asyncio
async def test_no_repository_writes_when_all_drafts_fail(monkeypatch):
    calls = _patch_chat_complete(
        monkeypatch,
        {"questions": [_draft(question_text="")]},
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert result.questions == []
    assert repository.saved_batches == []
    assert len(repository.logged) == 1
    assert len(repository.logged[0]) == 1
    # No structurally-valid drafts survived, so the judge is never invoked —
    # don't spend a large-model call auditing nothing.
    assert calls == [PROMPT_3_SYSTEM]


@pytest.mark.asyncio
async def test_response_carries_request_metadata(monkeypatch):
    _patch_chat_complete(monkeypatch, {"questions": [_draft()]})
    repository = FakeQuestionRepository()
    service = QuestionService(repository)
    request = _request()

    result = await service.generate_batch(request, _USER_ID)

    assert result.concept_id == request.concept_id
    assert result.bloom_level == request.bloom_level
    assert result.difficulty_tier == request.difficulty_tier
    assert result.questions[0].concept_id == request.concept_id


@pytest.mark.asyncio
async def test_judge_rejecting_answer_drops_a_structurally_valid_question(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {"questions": [_draft()]},
        judge_response={
            "verdicts": [
                {
                    "index": 0,
                    "requires_computation": False,
                    "derived_answers": ["Garbage collection"],
                    "bloom_aligned": True,
                    "concept_relevant": True,
                    "notes": "The stated answer is wrong.",
                }
            ]
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert result.questions == []
    assert repository.saved_batches == []
    logged_entries = repository.logged[0]
    assert len(logged_entries) == 1
    assert logged_entries[0]["validation_status"] == "Failed"
    assert "answer_correct" in logged_entries[0]["failed_checks"]
    assert logged_entries[0]["question_id"] is None


@pytest.mark.asyncio
async def test_judge_passes_structurally_valid_question_through(monkeypatch):
    calls = _patch_chat_complete(monkeypatch, {"questions": [_draft()]})
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert len(result.questions) == 1
    assert result.questions[0].validation_status == "Passed"
    assert calls == [PROMPT_3_SYSTEM, PROMPT_4_SYSTEM]


@pytest.mark.asyncio
async def test_missing_judge_verdict_fails_closed(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {"questions": [_draft()]},
        judge_response={"verdicts": []},
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert result.questions == []
    assert repository.saved_batches == []


@pytest.mark.asyncio
async def test_judge_catches_wrong_computational_answer(monkeypatch):
    # The actual bug found in live testing: Mistral generated a Doppler-shift
    # question and stated 544 Hz, when the correct value from its own stated
    # numbers is 548.4 Hz. The judge independently derives 548.4 and the
    # mismatch should drop the question.
    _patch_chat_complete(
        monkeypatch,
        {
            "questions": [
                _draft(
                    question_type="FillInBlank",
                    question_text=(
                        "A siren at 500 Hz approaches at 30 m/s; speed of sound is 340 m/s. "
                        "What frequency is heard?"
                    ),
                    options=None,
                    correct_answers=["544 Hz"],
                    explanation="500 * 340 / (340 - 30) = 544 Hz",
                )
            ]
        },
        judge_response={
            "verdicts": [
                {
                    "index": 0,
                    "requires_computation": True,
                    "derived_answers": ["548.4 Hz"],
                    "bloom_aligned": True,
                    "concept_relevant": True,
                    "notes": "",
                }
            ]
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert result.questions == []
    logged = repository.logged[0][0]
    assert logged["validation_status"] == "Failed"
    assert "answer_correct" in logged["failed_checks"]


@pytest.mark.asyncio
async def test_judge_tolerates_rounding_differences_in_computational_answers(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {
            "questions": [
                _draft(
                    question_type="FillInBlank",
                    question_text="What is 340 / 310 * 500?",
                    options=None,
                    correct_answers=["548 Hz"],
                    explanation="340/310*500 = 548.39 Hz, rounded to 548 Hz",
                )
            ]
        },
        judge_response={
            "verdicts": [
                {
                    "index": 0,
                    "requires_computation": True,
                    "derived_answers": ["548.39 Hz"],  # same value, different rounding
                    "bloom_aligned": True,
                    "concept_relevant": True,
                    "notes": "",
                }
            ]
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert len(result.questions) == 1
    assert result.questions[0].validation_status == "Passed"


@pytest.mark.asyncio
async def test_mixed_batch_structural_fail_judge_fail_and_pass(monkeypatch):
    # Three drafts, three different outcomes in one batch:
    # [0] fails structural validation (bad options) -> judge never sees it.
    # [1] passes structural but the judge rejects its answer.
    # [2] passes both.
    _patch_chat_complete(
        monkeypatch,
        {
            "questions": [
                _draft(options=["A", "A", "B"], correct_answers=["A"]),  # structural fail
                _draft(question_text="Q2?", correct_answers=["Ownership rules"]),  # judge fails
                _draft(question_text="Q3?", correct_answers=["Ownership rules"]),  # passes
            ]
        },
        judge_response={
            "verdicts": [
                {
                    "index": 0,
                    "requires_computation": False,
                    "derived_answers": ["Garbage collection"],
                    "bloom_aligned": True,
                    "concept_relevant": True,
                    "notes": "wrong",
                },
                {
                    "index": 1,
                    "requires_computation": False,
                    "derived_answers": ["Ownership rules"],
                    "bloom_aligned": True,
                    "concept_relevant": True,
                    "notes": "",
                },
            ]
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    # Only the third draft (index 2 pre-structural-drop -> index 1 post-drop,
    # matched to judge verdict index 1) survives.
    assert len(result.questions) == 1
    assert result.questions[0].question_text == "Q3?"
    assert len(repository.logged[0]) == 3
    statuses = [e["validation_status"] for e in repository.logged[0]]
    assert statuses.count("Failed") == 2
    assert statuses.count("Passed") == 1


@pytest.mark.asyncio
async def test_partial_missing_judge_verdict_only_drops_the_unjudged_question(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {
            "questions": [
                _draft(question_text="Q1?", correct_answers=["Ownership rules"]),
                _draft(question_text="Q2?", correct_answers=["Ownership rules"]),
            ]
        },
        # Only a verdict for index 0 — index 1's verdict is missing.
        judge_response={
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
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert len(result.questions) == 1
    assert result.questions[0].question_text == "Q1?"


@pytest.mark.asyncio
async def test_true_false_question_survives_full_pipeline(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {
            "questions": [
                _draft(
                    question_type="TrueFalse",
                    question_text="Does the borrow checker run at compile time?",
                    options=["True", "False"],
                    correct_answers=["True"],
                )
            ]
        },
        judge_response={
            "verdicts": [
                {
                    "index": 0,
                    "requires_computation": False,
                    "derived_answers": ["True"],
                    "bloom_aligned": True,
                    "concept_relevant": True,
                    "notes": "",
                }
            ]
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert len(result.questions) == 1
    assert result.questions[0].validation_status == "Passed"
    assert result.questions[0].question_type == "TrueFalse"


@pytest.mark.asyncio
async def test_fill_in_blank_question_survives_full_pipeline(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {
            "questions": [
                _draft(
                    question_type="FillInBlank",
                    question_text="The Rust compiler component that enforces ownership is the ___.",
                    options=None,
                    correct_answers=["borrow checker"],
                )
            ]
        },
        judge_response={
            "verdicts": [
                {
                    "index": 0,
                    "requires_computation": False,
                    "derived_answers": ["borrow checker"],
                    "bloom_aligned": True,
                    "concept_relevant": True,
                    "notes": "",
                }
            ]
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert len(result.questions) == 1
    assert result.questions[0].validation_status == "Passed"
    assert result.questions[0].question_type == "FillInBlank"


@pytest.mark.asyncio
async def test_multi_select_question_survives_full_pipeline(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {
            "questions": [
                _draft(
                    question_type="MCQMultiSelect",
                    question_text="Which of these are Rust ownership rules?",
                    options=[
                        "Each value has one owner",
                        "Values can have multiple owners",
                        "Borrows must not outlive the owner",
                        "Garbage collection reclaims memory",
                    ],
                    correct_answers=[
                        "Each value has one owner",
                        "Borrows must not outlive the owner",
                    ],
                )
            ]
        },
        judge_response={
            "verdicts": [
                {
                    "index": 0,
                    "requires_computation": False,
                    "derived_answers": [
                        "Borrows must not outlive the owner",
                        "Each value has one owner",
                    ],
                    "bloom_aligned": True,
                    "concept_relevant": True,
                    "notes": "",
                }
            ]
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert len(result.questions) == 1
    assert result.questions[0].validation_status == "Passed"
    assert result.questions[0].question_type == "MCQMultiSelect"
    assert set(result.questions[0].correct_answers) == {
        "Each value has one owner",
        "Borrows must not outlive the owner",
    }


@pytest.mark.asyncio
async def test_multi_select_question_dropped_when_judge_finds_different_set(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {
            "questions": [
                _draft(
                    question_type="MCQMultiSelect",
                    question_text="Which of these are Rust ownership rules?",
                    options=[
                        "Each value has one owner",
                        "Values can have multiple owners",
                        "Borrows must not outlive the owner",
                        "Garbage collection reclaims memory",
                    ],
                    correct_answers=[
                        "Each value has one owner",
                        "Borrows must not outlive the owner",
                    ],
                )
            ]
        },
        judge_response={
            "verdicts": [
                {
                    "index": 0,
                    "requires_computation": False,
                    "derived_answers": ["Each value has one owner"],
                    "bloom_aligned": True,
                    "concept_relevant": True,
                    "notes": "Only one of these is actually correct.",
                }
            ]
        },
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request(), _USER_ID)

    assert result.questions == []
    logged = repository.logged[0][0]
    assert logged["validation_status"] == "Failed"
    assert "answer_correct" in logged["failed_checks"]


# --- allowed_question_types restriction ---


def test_request_defaults_to_every_question_type():
    assert set(_request().allowed_question_types) == set(ALL_QUESTION_TYPES)


@pytest.mark.asyncio
async def test_generate_batch_restricts_prompt_3_schema_to_allowed_types(monkeypatch):
    captured_configs: list[CompletionConfig] = []

    async def fake(system_msg, user_msg, config):
        if system_msg == PROMPT_4_SYSTEM:
            return _DEFAULT_JUDGE_RESPONSE
        captured_configs.append(config)
        return {
            "questions": [
                _draft(
                    question_type="TrueFalse",
                    options=["True", "False"],
                    correct_answers=["True"],
                )
            ]
        }

    monkeypatch.setattr("question_generation_service.services.question_service.chat_complete", fake)
    repository = FakeQuestionRepository()
    service = QuestionService(repository)
    request = QuestionGenerationRequest(
        concept_id=uuid4(),
        concept_name="Borrow checker",
        learning_goal="Explain how the borrow checker enforces ownership",
        bloom_level="Understanding",
        difficulty_tier="medium",
        allowed_question_types=["TrueFalse"],
    )

    await service.generate_batch(request, _USER_ID)

    assert len(captured_configs) == 1
    json_schema = cast(JSONSchema, captured_configs[0].response_format.json_schema)
    schema = json_schema.schema_definition
    question_type_enum = schema["properties"]["questions"]["items"]["properties"]["question_type"][
        "enum"
    ]
    assert question_type_enum == ["TrueFalse"]


# --- pool reuse ---


@pytest.mark.asyncio
async def test_generate_batch_serves_unseen_pool_without_calling_llm(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError(
            "chat_complete should not be called when the pool fully covers the batch"
        )

    monkeypatch.setattr(
        "question_generation_service.services.question_service.chat_complete", fail_if_called
    )
    repository = FakeQuestionRepository()
    request = _request()
    repository.pool = [
        _pool_entry(
            request.concept_id,
            request.bloom_level,
            request.difficulty_tier,
            question_text=f"Q{i}",
        )
        for i in range(BATCH_SIZE)
    ]
    service = QuestionService(repository)

    result = await service.generate_batch(request, _USER_ID)

    assert len(result.questions) == BATCH_SIZE
    assert {q.question_text for q in result.questions} == {f"Q{i}" for i in range(BATCH_SIZE)}
    assert repository.saved_batches == []
    assert len(repository.mark_served_calls) == 1
    served_user, served_ids = repository.mark_served_calls[0]
    assert served_user == _USER_ID
    assert set(served_ids) == {q.id for q in result.questions}


@pytest.mark.asyncio
async def test_generate_batch_calls_llm_when_pool_is_fully_seen_by_this_user(monkeypatch):
    calls = _patch_chat_complete(monkeypatch, {"questions": [_draft()]})
    repository = FakeQuestionRepository()
    request = _request()
    seen_entries = [
        _pool_entry(request.concept_id, request.bloom_level, request.difficulty_tier)
        for _ in range(BATCH_SIZE)
    ]
    repository.pool = seen_entries
    repository.served[_USER_ID] = {e.id for e in seen_entries}
    service = QuestionService(repository)

    result = await service.generate_batch(request, _USER_ID)

    # Every pool entry was already served to this user, so none of them count
    # as "unseen" — generation must run rather than silently reusing them.
    assert calls == [PROMPT_3_SYSTEM, PROMPT_4_SYSTEM]
    assert len(result.questions) >= 1


@pytest.mark.asyncio
async def test_generate_batch_combines_unseen_pool_with_freshly_generated_shortfall(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {"questions": [_draft(question_text=f"New{i}") for i in range(3)]},
    )
    repository = FakeQuestionRepository()
    request = _request()
    unseen = [
        _pool_entry(
            request.concept_id,
            request.bloom_level,
            request.difficulty_tier,
            question_text=f"Unseen{i}",
        )
        for i in range(2)
    ]
    seen = [
        _pool_entry(
            request.concept_id,
            request.bloom_level,
            request.difficulty_tier,
            question_text=f"Seen{i}",
        )
        for i in range(3)
    ]
    repository.pool = unseen + seen
    repository.served[_USER_ID] = {e.id for e in seen}
    service = QuestionService(repository)

    result = await service.generate_batch(request, _USER_ID)

    # 2 unseen pool questions + 3 freshly generated to cover the shortfall —
    # the already-seen 3 never needed as a fallback, so they're excluded.
    texts = {q.question_text for q in result.questions}
    assert texts == {"Unseen0", "Unseen1", "New0", "New1", "New2"}


@pytest.mark.asyncio
async def test_generate_batch_falls_back_to_seen_pool_as_last_resort(monkeypatch):
    # Generation comes back empty (nothing usable) — with only 1 unseen pool
    # question available, the shortfall can only be covered by repeating
    # something this learner has already seen, rather than under-delivering.
    _patch_chat_complete(monkeypatch, {"questions": []})
    repository = FakeQuestionRepository()
    request = _request()
    unseen = [
        _pool_entry(
            request.concept_id,
            request.bloom_level,
            request.difficulty_tier,
            question_text="Unseen0",
        )
    ]
    seen = [
        _pool_entry(
            request.concept_id,
            request.bloom_level,
            request.difficulty_tier,
            question_text=f"Seen{i}",
        )
        for i in range(2)
    ]
    repository.pool = unseen + seen
    repository.served[_USER_ID] = {e.id for e in seen}
    service = QuestionService(repository)

    result = await service.generate_batch(request, _USER_ID)

    texts = {q.question_text for q in result.questions}
    assert texts == {"Unseen0", "Seen0", "Seen1"}
