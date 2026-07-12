from typing import Annotated

from fastapi import Depends

from question_generation_service.db.session import SessionDep
from question_generation_service.repositories.bkt_parameters_repository import (
    BktParametersRepository,
)
from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressRepository,
)
from question_generation_service.repositories.exposure_repository import ExposureRepository
from question_generation_service.repositories.learning_unit_repository import LearningUnitRepository
from question_generation_service.repositories.question_repository import QuestionRepository
from question_generation_service.repositories.quiz_repository import QuizRepository
from question_generation_service.repositories.session_repository import SessionRepository
from question_generation_service.repositories.thema_repository import ThemaRepository
from question_generation_service.services.adaptive_selection_service import (
    AdaptiveSelectionService,
)
from question_generation_service.services.bkt_init_service import BktInitService
from question_generation_service.services.concept_service import ConceptService
from question_generation_service.services.exposure_service import ExposureService
from question_generation_service.services.mastery_service import MasteryService
from question_generation_service.services.question_service import QuestionService
from question_generation_service.services.quiz_service import QuizService
from question_generation_service.services.session_service import SessionService
from question_generation_service.services.thema_service import ThemaService
from question_generation_service.services.wizard_service import WizardService


def get_learning_unit_repository(session: SessionDep) -> LearningUnitRepository:
    return LearningUnitRepository(session)


def get_concept_service(
    repository: Annotated[LearningUnitRepository, Depends(get_learning_unit_repository)],
) -> ConceptService:
    return ConceptService(repository)


def get_thema_repository(session: SessionDep) -> ThemaRepository:
    return ThemaRepository(session)


def get_exposure_repository(session: SessionDep) -> ExposureRepository:
    return ExposureRepository(session)


def get_concept_progress_repository(session: SessionDep) -> ConceptProgressRepository:
    return ConceptProgressRepository(session)


def get_bkt_init_service(
    repository: Annotated[ConceptProgressRepository, Depends(get_concept_progress_repository)],
) -> BktInitService:
    return BktInitService(repository)


def get_bkt_parameters_repository(session: SessionDep) -> BktParametersRepository:
    return BktParametersRepository(session)


def get_mastery_service(
    concept_progress_repository: Annotated[
        ConceptProgressRepository, Depends(get_concept_progress_repository)
    ],
    bkt_parameters_repository: Annotated[
        BktParametersRepository, Depends(get_bkt_parameters_repository)
    ],
    learning_unit_repository: Annotated[
        LearningUnitRepository, Depends(get_learning_unit_repository)
    ],
) -> MasteryService:
    return MasteryService(
        concept_progress_repository, bkt_parameters_repository, learning_unit_repository
    )


def get_thema_service(
    repository: Annotated[ThemaRepository, Depends(get_thema_repository)],
    concept_mapper: Annotated[ConceptService, Depends(get_concept_service)],
    exposure_repository: Annotated[ExposureRepository, Depends(get_exposure_repository)],
    bkt_init_service: Annotated[BktInitService, Depends(get_bkt_init_service)],
) -> ThemaService:
    return ThemaService(repository, concept_mapper, exposure_repository, bkt_init_service)


def get_exposure_service(
    thema_repository: Annotated[ThemaRepository, Depends(get_thema_repository)],
    exposure_repository: Annotated[ExposureRepository, Depends(get_exposure_repository)],
    learning_unit_repository: Annotated[
        LearningUnitRepository, Depends(get_learning_unit_repository)
    ],
    bkt_init_service: Annotated[BktInitService, Depends(get_bkt_init_service)],
) -> ExposureService:
    return ExposureService(
        thema_repository, exposure_repository, learning_unit_repository, bkt_init_service
    )


def get_wizard_service() -> WizardService:
    return WizardService()


def get_question_repository(session: SessionDep) -> QuestionRepository:
    return QuestionRepository(session)


def get_question_service(
    repository: Annotated[QuestionRepository, Depends(get_question_repository)],
) -> QuestionService:
    return QuestionService(repository)


def get_quiz_repository(session: SessionDep) -> QuizRepository:
    return QuizRepository(session)


def get_quiz_service(
    quiz_repository: Annotated[QuizRepository, Depends(get_quiz_repository)],
    learning_unit_repository: Annotated[
        LearningUnitRepository, Depends(get_learning_unit_repository)
    ],
) -> QuizService:
    return QuizService(quiz_repository, learning_unit_repository)


def get_session_repository(session: SessionDep) -> SessionRepository:
    return SessionRepository(session)


def get_adaptive_selection_service(
    concept_progress_repository: Annotated[
        ConceptProgressRepository, Depends(get_concept_progress_repository)
    ],
    question_repository: Annotated[QuestionRepository, Depends(get_question_repository)],
    question_service: Annotated[QuestionService, Depends(get_question_service)],
) -> AdaptiveSelectionService:
    return AdaptiveSelectionService(
        concept_progress_repository, question_repository, question_service
    )


def get_session_service(
    session_repository: Annotated[SessionRepository, Depends(get_session_repository)],
    quiz_repository: Annotated[QuizRepository, Depends(get_quiz_repository)],
    learning_unit_repository: Annotated[
        LearningUnitRepository, Depends(get_learning_unit_repository)
    ],
    question_repository: Annotated[QuestionRepository, Depends(get_question_repository)],
    mastery_service: Annotated[MasteryService, Depends(get_mastery_service)],
    adaptive_selection_service: Annotated[
        AdaptiveSelectionService, Depends(get_adaptive_selection_service)
    ],
) -> SessionService:
    return SessionService(
        session_repository,
        quiz_repository,
        learning_unit_repository,
        question_repository,
        mastery_service,
        adaptive_selection_service,
    )


ThemaServiceDep = Annotated[ThemaService, Depends(get_thema_service)]
ConceptServiceDep = Annotated[ConceptService, Depends(get_concept_service)]
WizardServiceDep = Annotated[WizardService, Depends(get_wizard_service)]
ExposureServiceDep = Annotated[ExposureService, Depends(get_exposure_service)]
QuestionServiceDep = Annotated[QuestionService, Depends(get_question_service)]
QuizServiceDep = Annotated[QuizService, Depends(get_quiz_service)]
SessionServiceDep = Annotated[SessionService, Depends(get_session_service)]
