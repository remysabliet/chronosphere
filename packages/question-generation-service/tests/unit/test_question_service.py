from uuid import UUID, uuid4

import pytest

from question_generation_service.repositories.question_repository import (
    QuestionInput,
    ValidationLogInput,
)
from question_generation_service.schemas.question import QuestionGenerationRequest
from question_generation_service.services.question_service import QuestionService


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
        self.correct_answer: str | None = question["correct_answer"]
        self.explanation: str | None = question["explanation"]
        self.estimated_time: str | None = question["estimated_time"]
        self.tags: list[str] | None = question["tags"]


class FakeQuestionRepository:
    def __init__(self) -> None:
        self.saved_batches: list[list[QuestionInput]] = []
        self.logged: list[list[ValidationLogInput]] = []

    async def save_batch(self, questions: list[QuestionInput]) -> list[_FakeEntry]:
        self.saved_batches.append(questions)
        return [_FakeEntry(uuid4(), question) for question in questions]

    async def log_validations(self, entries: list[ValidationLogInput]) -> None:
        self.logged.append(entries)


def _draft(
    question_type: str = "MCQ",
    question_text: str = "What does the borrow checker enforce?",
    options: list[str] | None = None,
    correct_answer: str = "Ownership rules",
    explanation: str = "It enforces Rust's ownership and borrowing rules at compile time.",
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


def _request() -> QuestionGenerationRequest:
    return QuestionGenerationRequest(
        concept_id=uuid4(),
        concept_name="Borrow checker",
        learning_goal="Explain how the borrow checker enforces ownership",
        bloom_level="Understanding",
        difficulty_tier="medium",
    )


def _patch_chat_complete(monkeypatch, response: dict[str, object]) -> None:
    async def fake(system_msg, user_msg, config):
        return response

    monkeypatch.setattr("question_generation_service.services.question_service.chat_complete", fake)


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

    result = await service.generate_batch(_request())

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

    await service.generate_batch(_request())

    assert len(repository.logged) == 1
    logged_entries = repository.logged[0]
    assert len(logged_entries) == 2
    statuses = {entry["validation_status"] for entry in logged_entries}
    assert statuses == {"Passed", "Failed"}
    failed_entry = next(e for e in logged_entries if e["validation_status"] == "Failed")
    assert failed_entry["question_id"] is None


@pytest.mark.asyncio
async def test_no_repository_writes_when_all_drafts_fail(monkeypatch):
    _patch_chat_complete(
        monkeypatch,
        {"questions": [_draft(question_text="")]},
    )
    repository = FakeQuestionRepository()
    service = QuestionService(repository)

    result = await service.generate_batch(_request())

    assert result.questions == []
    assert repository.saved_batches == []
    assert len(repository.logged) == 1
    assert len(repository.logged[0]) == 1


@pytest.mark.asyncio
async def test_response_carries_request_metadata(monkeypatch):
    _patch_chat_complete(monkeypatch, {"questions": [_draft()]})
    repository = FakeQuestionRepository()
    service = QuestionService(repository)
    request = _request()

    result = await service.generate_batch(request)

    assert result.concept_id == request.concept_id
    assert result.bloom_level == request.bloom_level
    assert result.difficulty_tier == request.difficulty_tier
    assert result.questions[0].concept_id == request.concept_id
