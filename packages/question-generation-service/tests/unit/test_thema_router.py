from unittest.mock import AsyncMock
from uuid import uuid4

from question_generation_service.dependencies.rate_limit import RateLimiter, ai_rate_limiter
from question_generation_service.main import app
from question_generation_service.schemas.exposure import ExposureResult
from question_generation_service.schemas.thema import (
    AmbiguousThema,
    ResolvedThema,
    ThemaCandidate,
    UnresolvedThema,
)


def _resolved(extraction_id=None):
    return ResolvedThema(
        extraction_id=extraction_id or uuid4(),
        thema="Photosynthesis",
        domain="Science",
        topics=["Light Reactions", "Calvin Cycle"],
        confidence=1.0,
        confirmation="You'll be quizzed on Photosynthesis.",
    )


def _ambiguous(extraction_id=None):
    candidates = [
        ThemaCandidate(
            rank=1,
            thema="If Statement",
            domain="Software",
            disambiguator="control flow",
            confidence=0.4,
            confirmation="c1",
            topics=["Syntax"],
        ),
        ThemaCandidate(
            rank=2,
            thema="English Conditionals",
            domain="Language",
            disambiguator="grammar",
            confidence=0.4,
            confirmation="c2",
            topics=["Zero", "First"],
        ),
    ]
    return AmbiguousThema(extraction_id=extraction_id or uuid4(), candidates=candidates)


def test_extract_returns_resolved(client, mock_thema_service):
    mock_thema_service.extract = AsyncMock(return_value=_resolved())
    response = client.post("/v1/thema/extract", json={"raw_user_input": "how plants make food"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "resolved"
    assert data["thema"] == "Photosynthesis"


def test_extract_returns_ambiguous(client, mock_thema_service):
    mock_thema_service.extract = AsyncMock(return_value=_ambiguous())
    response = client.post("/v1/thema/extract", json={"raw_user_input": "if"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ambiguous"
    assert len(data["candidates"]) == 2


def test_extract_returns_unresolved(client, mock_thema_service):
    mock_thema_service.extract = AsyncMock(return_value=UnresolvedThema(extraction_id=uuid4()))
    response = client.post("/v1/thema/extract", json={"raw_user_input": "asdf"})
    assert response.status_code == 200
    assert response.json()["status"] == "unresolved"


def test_extract_rejects_short_input(client, mock_thema_service):
    response = client.post("/v1/thema/extract", json={"raw_user_input": "a"})
    assert response.status_code == 422


def test_refine_returns_resolved(client, mock_thema_service):
    eid = uuid4()
    mock_thema_service.refine = AsyncMock(return_value=_resolved(eid))
    response = client.post(
        f"/v1/thema/{eid}/refine",
        json={"clarification": "I mean CPU architecture"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


def test_confirm_returns_resolved(client, mock_thema_service):
    eid = uuid4()
    mock_thema_service.confirm = AsyncMock(return_value=_resolved(eid))
    response = client.post(f"/v1/thema/{eid}/confirm", json={})
    assert response.status_code == 200
    assert response.json()["thema"] == "Photosynthesis"


def test_confirm_with_chosen_rank(client, mock_thema_service):
    eid = uuid4()
    mock_thema_service.confirm = AsyncMock(return_value=_resolved(eid))
    response = client.post(f"/v1/thema/{eid}/confirm", json={"chosen_rank": 2})
    assert response.status_code == 200
    mock_thema_service.confirm.assert_called_once()
    # confirm(extraction_id, body) — body is ConfirmRequest, check chosen_rank propagated
    call_args = mock_thema_service.confirm.call_args
    body = call_args[0][1] if call_args[0] else call_args[1]["body"]
    assert body.chosen_rank == 2


def test_router_requires_auth(anon_client):
    """No auth override — bearer token is missing → 403 or 401."""
    response = anon_client.post("/v1/thema/extract", json={"raw_user_input": "photosynthesis"})
    assert response.status_code in (401, 403)


def test_confirm_propagates_exposure_required(client, mock_thema_service):
    eid = uuid4()
    resolved = _resolved(eid)
    resolved.exposure_required = True
    mock_thema_service.confirm = AsyncMock(return_value=resolved)
    response = client.post(f"/v1/thema/{eid}/confirm", json={})
    assert response.status_code == 200
    assert response.json()["exposure_required"] is True


def test_submit_exposure_returns_result(client, mock_exposure_service):
    eid = uuid4()
    mock_exposure_service.submit = AsyncMock(
        return_value=ExposureResult(
            thema="Photosynthesis", exposure_level="Practiced", p_l0=0.6, concepts_initialized=4
        )
    )
    response = client.post(f"/v1/thema/{eid}/exposure", json={"exposure_level": "Practiced"})
    assert response.status_code == 200
    data = response.json()
    assert data["p_l0"] == 0.6
    assert data["concepts_initialized"] == 4


def test_extract_rate_limited_after_threshold(client, mock_thema_service):
    mock_thema_service.extract = AsyncMock(return_value=_resolved())
    app.dependency_overrides[ai_rate_limiter] = RateLimiter(max_requests=1, window_seconds=60)
    try:
        first = client.post("/v1/thema/extract", json={"raw_user_input": "how plants make food"})
        second = client.post("/v1/thema/extract", json={"raw_user_input": "how plants make food"})
    finally:
        del app.dependency_overrides[ai_rate_limiter]

    assert first.status_code == 200
    assert second.status_code == 429
