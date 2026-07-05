import pytest

from question_generation_service.schemas.question import GeneratedQuestion
from question_generation_service.services.question_validation_service import validate_question


def _mcq(
    question_text: str = "What does the borrow checker enforce?",
    options: list[str] | None = None,
    correct_answer: str = "Ownership rules",
    explanation: str = "The borrow checker enforces Rust's ownership and borrowing rules at compile time.",
) -> GeneratedQuestion:
    return GeneratedQuestion(
        question_type="MCQ",
        question_text=question_text,
        options=options
        if options is not None
        else ["Ownership rules", "Garbage collection", "Type inference", "Macros"],
        correct_answer=correct_answer,
        explanation=explanation,
        estimated_time_seconds=30,
        tags=["rust"],
    )


def test_valid_mcq_passes():
    result = validate_question(_mcq())
    assert result["status"] == "Passed"
    assert result["failed_checks"] == []
    assert result["score"] == 1.0


def test_valid_true_false_passes():
    question = GeneratedQuestion(
        question_type="TrueFalse",
        question_text="Rust has a garbage collector.",
        options=["True", "False"],
        correct_answer="False",
        explanation="Rust uses ownership and borrowing instead of a garbage collector.",
        estimated_time_seconds=15,
        tags=[],
    )
    assert validate_question(question)["status"] == "Passed"


def test_valid_fill_in_blank_passes():
    question = GeneratedQuestion(
        question_type="FillInBlank",
        question_text="The Rust compiler that enforces ownership is called the ___.",
        options=None,
        correct_answer="borrow checker",
        explanation="This component checks ownership and borrowing rules at compile time.",
        estimated_time_seconds=20,
        tags=[],
    )
    assert validate_question(question)["status"] == "Passed"


def test_empty_stem_fails():
    result = validate_question(_mcq(question_text="   "))
    assert result["status"] == "Failed"
    assert "stem_present" in result["failed_checks"]


def test_answer_not_in_options_fails():
    result = validate_question(_mcq(correct_answer="Something else"))
    assert result["status"] == "Failed"
    assert "answer_in_options" in result["failed_checks"]


def test_duplicate_options_fail():
    result = validate_question(_mcq(options=["A", "A", "B", "C"], correct_answer="A"))
    assert result["status"] == "Failed"
    assert "options_unique" in result["failed_checks"]


@pytest.mark.parametrize("option_count", [1, 6])
def test_mcq_option_count_out_of_range_fails(option_count):
    options = [f"Option {i}" for i in range(option_count)]
    result = validate_question(_mcq(options=options, correct_answer=options[0]))
    assert result["status"] == "Failed"
    assert "valid_option_shape" in result["failed_checks"]


def test_true_false_wrong_options_fails():
    question = GeneratedQuestion(
        question_type="TrueFalse",
        question_text="Rust has a garbage collector.",
        options=["Yes", "No"],
        correct_answer="No",
        explanation="Rust uses ownership and borrowing instead of a garbage collector.",
        estimated_time_seconds=15,
        tags=[],
    )
    result = validate_question(question)
    assert result["status"] == "Failed"
    assert "valid_option_shape" in result["failed_checks"]


def test_fill_in_blank_with_options_fails():
    question = GeneratedQuestion(
        question_type="FillInBlank",
        question_text="The ___ enforces ownership.",
        options=["borrow checker"],
        correct_answer="borrow checker",
        explanation="This component checks ownership and borrowing rules at compile time.",
        estimated_time_seconds=20,
        tags=[],
    )
    result = validate_question(question)
    assert result["status"] == "Failed"
    assert "valid_option_shape" in result["failed_checks"]


def test_short_explanation_is_warning_not_failed():
    result = validate_question(_mcq(explanation="Because."))
    assert result["status"] == "Warning"
    assert result["failed_checks"] == ["explanation_quality"]
