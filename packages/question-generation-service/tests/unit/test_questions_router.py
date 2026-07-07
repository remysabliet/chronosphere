from unittest.mock import AsyncMock
from uuid import uuid4

from question_generation_service.schemas.question import QuestionBatchResponse, StoredQuestion


def _batch_response(concept_id) -> QuestionBatchResponse:
    return QuestionBatchResponse(
        concept_id=concept_id,
        bloom_level="Understanding",
        difficulty_tier="medium",
        questions=[
            StoredQuestion(
                id=uuid4(),
                concept_id=concept_id,
                bloom_level="Understanding",
                difficulty_tier="medium",
                question_type="MCQ",
                question_text="What does the borrow checker enforce?",
                options=["Ownership rules", "Garbage collection"],
                correct_answers=["Ownership rules"],
                explanation="It enforces Rust's ownership rules at compile time.",
                estimated_time_seconds=30,
                tags=["rust"],
                validation_status="Passed",
            )
        ],
    )


def test_generate_questions_returns_batch(client, mock_question_service):
    concept_id = uuid4()
    mock_question_service.generate_batch = AsyncMock(return_value=_batch_response(concept_id))

    response = client.post(
        "/v1/questions/generate",
        json={
            "concept_id": str(concept_id),
            "concept_name": "Borrow checker",
            "learning_goal": "Explain how the borrow checker enforces ownership",
            "bloom_level": "Understanding",
            "difficulty_tier": "medium",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["concept_id"] == str(concept_id)
    assert len(data["questions"]) == 1
    assert data["questions"][0]["validation_status"] == "Passed"


def test_generate_questions_requires_auth(anon_client):
    response = anon_client.post(
        "/v1/questions/generate",
        json={
            "concept_id": str(uuid4()),
            "concept_name": "Borrow checker",
            "learning_goal": "Explain ownership",
            "bloom_level": "Understanding",
            "difficulty_tier": "medium",
        },
    )
    assert response.status_code in (401, 403)


def test_generate_questions_rejects_invalid_bloom_level(client, mock_question_service):
    response = client.post(
        "/v1/questions/generate",
        json={
            "concept_id": str(uuid4()),
            "concept_name": "Borrow checker",
            "learning_goal": "Explain ownership",
            "bloom_level": "NotARealLevel",
            "difficulty_tier": "medium",
        },
    )
    assert response.status_code == 422
