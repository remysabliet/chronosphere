from typing import TypedDict

from question_generation_service.schemas.question import GeneratedQuestion, ValidationStatus

# Structural checks a broken question can't be served at all — fail these and
# the draft is dropped instead of stored (main-workflow.md Step 8A).
_CRITICAL_CHECKS = frozenset(
    {"stem_present", "valid_option_shape", "options_unique", "answer_in_options"}
)
# Quality checks that matter but don't make the question unusable — fail one of
# these and the question is still stored, flagged "Warning" for review.
_MIN_EXPLANATION_LENGTH = 15


class ValidationResult(TypedDict):
    status: ValidationStatus
    failed_checks: list[str]
    score: float


def _option_checks(question: GeneratedQuestion) -> dict[str, bool]:
    options = question.options or []
    if question.question_type == "MCQ":
        return {
            "valid_option_shape": 2 <= len(options) <= 5,
            "options_unique": len(options) == len(set(options)),
            "answer_in_options": question.correct_answer in options,
        }
    if question.question_type == "TrueFalse":
        return {
            "valid_option_shape": set(options) == {"True", "False"},
            "options_unique": True,
            "answer_in_options": question.correct_answer in {"True", "False"},
        }
    # FillInBlank: no options, the answer just needs to be a real value.
    return {
        "valid_option_shape": not options,
        "options_unique": True,
        "answer_in_options": bool(question.correct_answer.strip()),
    }


def validate_question(question: GeneratedQuestion) -> ValidationResult:
    checks: dict[str, bool] = {
        "stem_present": bool(question.question_text.strip()),
        **_option_checks(question),
        "explanation_quality": len(question.explanation.strip()) >= _MIN_EXPLANATION_LENGTH,
    }

    failed_checks = [name for name, ok in checks.items() if not ok]
    score = (len(checks) - len(failed_checks)) / len(checks)

    if any(name in _CRITICAL_CHECKS for name in failed_checks):
        status: ValidationStatus = "Failed"
    elif failed_checks:
        status = "Warning"
    else:
        status = "Passed"

    return ValidationResult(status=status, failed_checks=failed_checks, score=score)
