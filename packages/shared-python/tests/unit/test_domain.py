from typing import get_args

from memosphere_domain import (
    EXPOSURE_TO_P_L0,
    BloomLevel,
    ComplexityLevel,
    DifficultyTier,
    ExposureLevel,
    QuestionType,
    ValidationStatus,
)


def test_bloom_level_has_six_canonical_values():
    assert get_args(BloomLevel) == (
        "Remembering",
        "Understanding",
        "Applying",
        "Analyzing",
        "Evaluating",
        "Creating",
    )


def test_complexity_level_values():
    assert set(get_args(ComplexityLevel)) == {"Low", "Medium", "High"}


def test_question_type_values():
    assert set(get_args(QuestionType)) == {"MCQ", "MCQMultiSelect", "TrueFalse", "FillInBlank"}


def test_difficulty_tier_values():
    assert set(get_args(DifficultyTier)) == {"easy", "medium", "hard"}


def test_validation_status_values():
    assert set(get_args(ValidationStatus)) == {"Passed", "Failed", "Warning"}


def test_exposure_to_p_l0_covers_every_exposure_level():
    assert set(EXPOSURE_TO_P_L0.keys()) == set(get_args(ExposureLevel))


def test_exposure_to_p_l0_is_monotonically_increasing():
    ordered = [
        EXPOSURE_TO_P_L0[level] for level in ("Unseen", "Recognized", "Practiced", "Mastered")
    ]
    assert ordered == sorted(ordered)
