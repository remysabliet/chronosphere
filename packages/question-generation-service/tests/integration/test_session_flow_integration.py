"""End-to-end quiz-taking flow against real Postgres: create a quiz + store
real questions for it, start a session, answer every question (mixing right
and wrong), and verify quiz_sessions/user_responses land correctly in the
actual (partitioned) tables — the ORM/DB layer here has no fakes to hide
behind, unlike the unit tests in test_session_service.py.
"""

import uuid

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from question_generation_service.core.config import get_settings
from question_generation_service.core.exceptions import InvalidInputError
from question_generation_service.repositories.bkt_parameters_repository import (
    BktParametersRepository,
)
from question_generation_service.repositories.concept_progress_repository import (
    ConceptProgressInput,
    ConceptProgressRepository,
)
from question_generation_service.repositories.learning_unit_repository import (
    ConceptInput,
    LearningUnitRepository,
)
from question_generation_service.repositories.question_repository import (
    QuestionInput,
    QuestionRepository,
)
from question_generation_service.repositories.quiz_repository import QuizRepository
from question_generation_service.repositories.session_repository import SessionRepository
from question_generation_service.repositories.user_repository import UserRepository
from question_generation_service.schemas.quiz import QuizCreateRequest
from question_generation_service.schemas.session import SubmitAnswerRequest
from question_generation_service.services.adaptive_selection_service import (
    AdaptiveSelectionService,
)
from question_generation_service.services.mastery_service import MasteryService, update_bkt
from question_generation_service.services.question_service import QuestionService
from question_generation_service.services.quiz_service import QuizService
from question_generation_service.services.session_service import SessionService

pytestmark = pytest.mark.asyncio


def _concept_input(name: str) -> ConceptInput:
    return ConceptInput(
        topic="Topic",
        concept_name=name,
        learning_goal=f"Master {name}",
        bloom_levels_supported=["Remembering"],
        estimated_time_minutes=10,
        bloom_coverage_score=3,
        complexity_level="Medium",
        embedding=[0.0] * 1024,
    )


async def test_session_flow_end_to_end():
    settings = get_settings()
    engine = create_async_engine(
        settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    )
    session_factory = async_sessionmaker(bind=engine, expire_on_commit=False)

    user_id = uuid.uuid4()
    thema = f"Session Flow Thema {uuid.uuid4().hex[:8]}"
    empty_thema = f"Empty Thema {uuid.uuid4().hex[:8]}"

    async with session_factory() as setup_session:
        await setup_session.execute(
            text(
                "INSERT INTO users (user_id, name, email, created_at) "
                "VALUES (:user_id, 'Session Flow User', :email, now())"
            ),
            {"user_id": str(user_id), "email": f"{user_id}@example.com"},
        )
        await setup_session.commit()

        unit_repository = LearningUnitRepository(setup_session)
        units = await unit_repository.save_batch(thema, [_concept_input("Concept A")])
        concept_id = units[0].id
        empty_units = await unit_repository.save_batch(empty_thema, [_concept_input("Concept B")])

        # MasteryService.record_attempt requires an existing BKT state row —
        # normally seeded by BktInitService on thema confirmation, which this
        # test bypasses by writing learning units directly.
        concept_progress_repository = ConceptProgressRepository(setup_session)
        initial_p_ln = 0.2
        await concept_progress_repository.initialize_batch(
            user_id,
            [
                ConceptProgressInput(
                    concept_id=concept_id, bloom_level="Remembering", p_ln=initial_p_ln
                )
            ],
        )

        # Fetched (not hardcoded) so the expected-p_ln math below tracks
        # whatever seed data is actually live, the same way MasteryService
        # itself looks these up — _concept_input sets complexity_level="Medium"
        # and every stored question here uses bloom_level="Remembering".
        bkt_parameters_repository = BktParametersRepository(setup_session)
        bkt_defaults = await bkt_parameters_repository.get_defaults("Medium")
        assert bkt_defaults is not None
        bloom_weight = await bkt_parameters_repository.get_bloom_weight("Remembering") or 1.0

        question_repository = QuestionRepository(setup_session)
        stored = await question_repository.save_batch(
            [
                QuestionInput(
                    concept_id=concept_id,
                    bloom_level="Remembering",
                    difficulty_tier="medium",
                    question_type="MCQ",
                    question_text=f"Question {i}?",
                    options=["A", "B"],
                    correct_answers=["A"],
                    explanation="Because A.",
                    estimated_time="30",
                    tags=[],
                    # One-hot and orthogonal per question — a shared or
                    # all-zero vector would make the two questions register
                    # as "too similar to something already served" (or hit
                    # cosine distance's undefined zero-vector case) once the
                    # first is marked served, and the session would never
                    # advance to the second.
                    embedding=[1.0 if j == i else 0.0 for j in range(1024)],
                )
                for i in range(2)
            ]
        )

        quiz_service = QuizService(QuizRepository(setup_session), unit_repository)
        quiz = await quiz_service.create(
            user_id,
            QuizCreateRequest(thema=thema, question_types=["MCQ"], question_count=2),
        )
        empty_quiz = await quiz_service.create(
            user_id,
            QuizCreateRequest(thema=empty_thema, question_types=["MCQ"], question_count=2),
        )
        assert empty_units  # sanity: the empty quiz's thema really did map to a unit

    try:
        async with session_factory() as service_session:
            service_unit_repository = LearningUnitRepository(service_session)
            service_question_repository = QuestionRepository(service_session)
            service_concept_progress_repository = ConceptProgressRepository(service_session)
            mastery_service = MasteryService(
                service_concept_progress_repository,
                BktParametersRepository(service_session),
                service_unit_repository,
            )
            adaptive_selection_service = AdaptiveSelectionService(
                service_concept_progress_repository,
                service_question_repository,
                QuestionService(service_question_repository),
            )
            session_service = SessionService(
                SessionRepository(service_session),
                QuizRepository(service_session),
                service_unit_repository,
                service_question_repository,
                mastery_service,
                adaptive_selection_service,
                UserRepository(service_session),
            )

            # 1. Starting pulls exactly the 2 stored questions into a frozen order.
            state = await session_service.start(quiz.id, user_id, "immediate")
            assert state.total_questions == 2
            assert state.session_complete is False
            assert state.question is not None
            assert state.question.id in {s.id for s in stored}

            first_id = state.question.id
            # 2. First answer: deliberately wrong.
            result = await session_service.submit_answer(
                state.session_id,
                user_id,
                SubmitAnswerRequest(question_id=first_id, selected=["B"]),
            )
            assert result.is_correct is False
            assert result.correct_answers == ["A"]
            assert result.state.session_complete is False
            assert result.state.question is not None

            # Ground truth computed independently via the same pure BKT
            # function MasteryService wraps — cross-checks that submitting an
            # answer through the full HTTP-shaped flow moved this concept's
            # p_ln by exactly the amount the formula predicts, not just "some
            # amount in the right direction".
            expected_p_ln_after_wrong = update_bkt(
                initial_p_ln,
                p_t=bkt_defaults.P_T,
                p_g=bkt_defaults.P_G or 0.0,
                p_s=bkt_defaults.P_S or 0.0,
                response_score=0.0,
                bloom_weight=bloom_weight,
            )
            row_after_wrong = (
                await service_session.execute(
                    text(
                        "SELECT p_ln, mastery_status, attempt_count, correct_count, slip_count "
                        "FROM concept_progress_tracker "
                        "WHERE user_id = :user_id AND concept_id = :concept_id "
                        "AND bloom_level = 'Remembering'"
                    ),
                    {"user_id": str(user_id), "concept_id": str(concept_id)},
                )
            ).one()
            assert row_after_wrong.p_ln == pytest.approx(expected_p_ln_after_wrong)
            assert row_after_wrong.attempt_count == 1
            assert row_after_wrong.correct_count == 0
            assert row_after_wrong.slip_count == 1

            # 3. Second answer: correct, and the last one — completes the session.
            second_id = result.state.question.id
            result2 = await session_service.submit_answer(
                state.session_id,
                user_id,
                SubmitAnswerRequest(question_id=second_id, selected=["A"]),
            )
            assert result2.is_correct is True
            assert result2.state.session_complete is True
            assert result2.state.question is None

            expected_p_ln_after_correct = update_bkt(
                expected_p_ln_after_wrong,
                p_t=bkt_defaults.P_T,
                p_g=bkt_defaults.P_G or 0.0,
                p_s=bkt_defaults.P_S or 0.0,
                response_score=1.0,
                bloom_weight=bloom_weight,
            )
            row_after_correct = (
                await service_session.execute(
                    text(
                        "SELECT p_ln, mastery_status, attempt_count, correct_count, slip_count "
                        "FROM concept_progress_tracker "
                        "WHERE user_id = :user_id AND concept_id = :concept_id "
                        "AND bloom_level = 'Remembering'"
                    ),
                    {"user_id": str(user_id), "concept_id": str(concept_id)},
                )
            ).one()
            assert row_after_correct.p_ln == pytest.approx(expected_p_ln_after_correct)
            assert row_after_correct.p_ln > row_after_wrong.p_ln
            assert row_after_correct.attempt_count == 2
            assert row_after_correct.correct_count == 1
            assert row_after_correct.slip_count == 1

            summary = await session_service.summary(state.session_id, user_id)
            assert summary.total_questions == 2
            assert summary.correct_answers == 1
            assert summary.status == "completed"

            # 4. Starting on a quiz with zero stored questions must raise, not
            # silently return an empty session.
            with pytest.raises(InvalidInputError):
                await session_service.start(empty_quiz.id, user_id, None)

        # Verify the raw rows really landed correctly, including the
        # partitioned user_responses table.
        async with session_factory() as verify_session:
            row = await verify_session.execute(
                text(
                    "SELECT session_status, total_questions, correct_answers, quiz_id "
                    "FROM quiz_sessions WHERE session_id = :id"
                ),
                {"id": str(state.session_id)},
            )
            session_status, total_questions, correct_answers, quiz_id = row.one()
            assert session_status == "completed"
            assert total_questions == 2
            assert correct_answers == 1
            assert quiz_id == quiz.id

            responses = await verify_session.execute(
                text(
                    "SELECT is_correct, question_sequence_order FROM user_responses "
                    "WHERE session_id = :id ORDER BY question_sequence_order"
                ),
                {"id": str(state.session_id)},
            )
            rows = responses.all()
            assert [r[1] for r in rows] == [0, 1]
            assert [r[0] for r in rows] == [False, True]
    finally:
        async with session_factory() as cleanup_session:
            await cleanup_session.execute(
                text("DELETE FROM user_responses WHERE user_id = :id"), {"id": str(user_id)}
            )
            await cleanup_session.execute(
                text("DELETE FROM quiz_sessions WHERE user_id = :id"), {"id": str(user_id)}
            )
            await cleanup_session.execute(
                text("DELETE FROM quizzes WHERE owner_user_id = :id"), {"id": str(user_id)}
            )
            await cleanup_session.execute(
                text("DELETE FROM outbox WHERE payload->>'owner_user_id' = :owner"),
                {"owner": str(user_id)},
            )
            await cleanup_session.execute(
                text("DELETE FROM questions WHERE concept_id = :cid"), {"cid": str(concept_id)}
            )
            await cleanup_session.execute(
                text("DELETE FROM learning_units WHERE thema IN (:t1, :t2)"),
                {"t1": thema, "t2": empty_thema},
            )
            await cleanup_session.execute(
                text("DELETE FROM users WHERE user_id = :id"), {"id": str(user_id)}
            )
            await cleanup_session.commit()
        await engine.dispose()
