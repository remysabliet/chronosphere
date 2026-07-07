"""Domain enums shared across Memosphere's Python services.

Each of these maps directly to a Postgres CHECK constraint or a fixed value
set used by more than one service (question-generation-service today;
learning-engine-service will need BloomLevel/ExposureLevel for BKT). Define
them once here rather than letting each service redeclare its own copy.
"""

from typing import Literal, get_args

BloomLevel = Literal[
    "Remembering",
    "Understanding",
    "Applying",
    "Analyzing",
    "Evaluating",
    "Creating",
]

ComplexityLevel = Literal["Low", "Medium", "High"]

QuestionType = Literal["MCQ", "MCQMultiSelect", "TrueFalse", "FillInBlank"]
# Single source of truth for "every type that exists" — e.g. the default when
# a caller doesn't restrict which types to generate.
ALL_QUESTION_TYPES: list[QuestionType] = list(get_args(QuestionType))

DifficultyTier = Literal["easy", "medium", "hard"]

ValidationStatus = Literal["Passed", "Failed", "Warning"]

ExposureLevel = Literal["Unseen", "Recognized", "Practiced", "Mastered"]

# Step 5/7 (main-workflow.md): flat starting P(L0) per self-reported exposure
# level, applied uniformly across every concept-Bloom pair until the
# placement probe and later BKT updates differentiate them.
EXPOSURE_TO_P_L0: dict[ExposureLevel, float] = {
    "Unseen": 0.2,
    "Recognized": 0.4,
    "Practiced": 0.6,
    "Mastered": 0.8,
}
