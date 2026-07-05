from unittest.mock import MagicMock

from question_generation_service.dependencies.services import (
    get_concept_service,
    get_thema_repository,
    get_thema_service,
)
from question_generation_service.repositories.thema_repository import ThemaRepository
from question_generation_service.services.concept_service import ConceptService
from question_generation_service.services.thema_service import ThemaService


def test_get_thema_repository_returns_repository():
    session = MagicMock()
    repo = get_thema_repository(session)
    assert isinstance(repo, ThemaRepository)
    assert repo.session is session


def test_get_thema_service_returns_service():
    session = MagicMock()
    repo = get_thema_repository(session)
    concept_service = get_concept_service(MagicMock())
    service = get_thema_service(repo, concept_service)
    assert isinstance(service, ThemaService)
    assert service.repository is repo
    assert isinstance(service.concept_mapper, ConceptService)
