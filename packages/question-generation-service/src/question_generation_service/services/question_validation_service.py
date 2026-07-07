import re
from typing import TypedDict

from memosphere_domain import ValidationStatus
from question_generation_service.schemas.question import GeneratedQuestion, JudgeVerdict

# The actual bug this exists to catch (544 Hz stated vs 548.4 Hz correct) was
# only ~0.8% off — tight enough that a loose tolerance would have missed the
# exact error that motivated this check. 0.5% still tolerates legitimate
# rounding-to-fewer-digits differences without accepting a wrong computation.
# Handles thousands separators ("1,234.5") and scientific notation ("3.5e8").
_NUMBER_PATTERN = re.compile(r"-?\d[\d,]*\.?\d*(?:[eE][-+]?\d+)?")
_NUMERIC_RELATIVE_TOLERANCE = 0.005
_TRAILING_PUNCTUATION = ".,!?;:"

# Structural checks a broken question can't be served at all — fail these and
# the draft is dropped instead of stored (main-workflow.md Step 8A).
_CRITICAL_CHECKS = frozenset(
    {"stem_present", "valid_option_shape", "options_unique", "answer_in_options"}
)
# Quality checks that matter but don't make the question unusable — fail one of
# these and the question is still stored, flagged "Warning" for review.
_MIN_EXPLANATION_LENGTH = 15
# stem_present, valid_option_shape, options_unique, answer_in_options, explanation_quality
_DETERMINISTIC_CHECK_COUNT = 5


class ValidationResult(TypedDict):
    status: ValidationStatus
    failed_checks: list[str]
    score: float


def _option_checks(question: GeneratedQuestion) -> dict[str, bool]:
    options = question.options or []
    # Stripped so stray trailing/leading space on the model's stated answers
    # (e.g. "Ownership rules " vs "Ownership rules") doesn't fail an otherwise
    # correct question — the option list itself isn't re-ordered or altered.
    stripped_options = {o.strip() for o in options}
    stripped_answers = [a.strip() for a in question.correct_answers]

    if question.question_type == "MCQ":
        return {
            "valid_option_shape": 2 <= len(options) <= 5,
            "options_unique": len(options) == len(set(options)),
            "answer_in_options": (
                len(stripped_answers) == 1 and stripped_answers[0] in stripped_options
            ),
        }
    if question.question_type == "MCQMultiSelect":
        return {
            "valid_option_shape": 3 <= len(options) <= 6,
            "options_unique": len(options) == len(set(options)),
            # At least 2 correct answers, never all of them (needs a distractor),
            # no duplicates among the answers themselves, all must be real options.
            "answer_in_options": (
                2 <= len(stripped_answers) < len(options)
                and len(stripped_answers) == len(set(stripped_answers))
                and stripped_options.issuperset(stripped_answers)
            ),
        }
    if question.question_type == "TrueFalse":
        return {
            "valid_option_shape": set(options) == {"True", "False"},
            "options_unique": True,
            "answer_in_options": (
                len(stripped_answers) == 1 and stripped_answers[0] in {"True", "False"}
            ),
        }
    # FillInBlank: no options, the answer just needs to be a single real value.
    return {
        "valid_option_shape": not options,
        "options_unique": True,
        "answer_in_options": len(stripped_answers) == 1 and bool(stripped_answers[0]),
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


_JUDGE_CHECK_COUNT = 3  # answer_correct, bloom_aligned, concept_relevant


def _extract_number(text: str) -> float | None:
    match = _NUMBER_PATTERN.search(text)
    return float(match.group().replace(",", "")) if match else None


def _normalize_text_answer(text: str) -> str:
    return text.strip().rstrip(_TRAILING_PUNCTUATION).casefold()


def answers_match(
    derived_answers: list[str], stated_answers: list[str], requires_computation: bool
) -> bool:
    """Compares the judge's independently-derived answer(s) against the
    draft's stated one(s) — programmatically, not via the judge's own
    self-report, since a model can mark "correct" as true without truly
    re-deriving anything.

    A single-answer question is just the multi-select case with one element,
    so both are compared the same way: as sets, order-independent. Non-
    computational answers are compared as text (case/whitespace/trailing-
    punctuation-insensitive — the judge and generator can phrase the same
    answer with or without a trailing period). Computational questions only
    make sense with exactly one answer each, compared as numbers within a
    relative tolerance, since "548 Hz" and "548.39 Hz" are the same answer,
    just rounded differently.
    """
    if requires_computation:
        if len(derived_answers) != 1 or len(stated_answers) != 1:
            return False
        derived_number = _extract_number(derived_answers[0])
        stated_number = _extract_number(stated_answers[0])
        if derived_number is None or stated_number is None:
            return False
        if stated_number == 0:
            return abs(derived_number - stated_number) < 1e-9
        return (
            abs(derived_number - stated_number) / abs(stated_number) <= _NUMERIC_RELATIVE_TOLERANCE
        )

    derived_set = {_normalize_text_answer(a) for a in derived_answers}
    stated_set = {_normalize_text_answer(a) for a in stated_answers}
    return derived_set == stated_set


def merge_judge_verdict(
    result: ValidationResult, question: GeneratedQuestion, verdict: JudgeVerdict
) -> ValidationResult:
    """Folds Prompt 4's independent re-derivation into a structural result.

    Only called on drafts that already passed structural checks — any judge
    check failing here means the content is actually wrong, misaligned, or
    off-topic, so it always drops the question rather than downgrading to a
    Warning.
    """
    answer_ok = answers_match(
        verdict.derived_answers, question.correct_answers, verdict.requires_computation
    )
    judge_failed = [
        name
        for name, ok in (
            ("answer_correct", answer_ok),
            ("bloom_aligned", verdict.bloom_aligned),
            ("concept_relevant", verdict.concept_relevant),
        )
        if not ok
    ]
    if not judge_failed:
        return result

    all_failed = [*result["failed_checks"], *judge_failed]
    total_checks = _DETERMINISTIC_CHECK_COUNT + _JUDGE_CHECK_COUNT
    return ValidationResult(
        status="Failed",
        failed_checks=all_failed,
        score=(total_checks - len(all_failed)) / total_checks,
    )
