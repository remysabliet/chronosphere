import pytest

from question_generation_service.schemas.question import GeneratedQuestion, JudgeVerdict
from question_generation_service.services.question_validation_service import (
    answers_match,
    merge_judge_verdict,
    validate_question,
)


def _mcq(
    question_text: str = "What does the borrow checker enforce?",
    options: list[str] | None = None,
    correct_answers: list[str] | None = None,
    explanation: str = "The borrow checker enforces Rust's ownership and borrowing rules at compile time.",
) -> GeneratedQuestion:
    return GeneratedQuestion(
        question_type="MCQ",
        question_text=question_text,
        options=options
        if options is not None
        else ["Ownership rules", "Garbage collection", "Type inference", "Macros"],
        correct_answers=correct_answers if correct_answers is not None else ["Ownership rules"],
        explanation=explanation,
        estimated_time_seconds=30,
        tags=["rust"],
    )


def _multi_select(
    question_text: str = "Which of these are Rust ownership rules?",
    options: list[str] | None = None,
    correct_answers: list[str] | None = None,
    explanation: str = "Both rules come directly from Rust's ownership model.",
) -> GeneratedQuestion:
    return GeneratedQuestion(
        question_type="MCQMultiSelect",
        question_text=question_text,
        options=options
        if options is not None
        else [
            "Each value has one owner",
            "Values can have multiple owners",
            "Borrows must not outlive the owner",
            "Garbage collection reclaims memory",
        ],
        correct_answers=correct_answers
        if correct_answers is not None
        else ["Each value has one owner", "Borrows must not outlive the owner"],
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
        correct_answers=["False"],
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
        correct_answers=["borrow checker"],
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
    result = validate_question(_mcq(correct_answers=["Something else"]))
    assert result["status"] == "Failed"
    assert "answer_in_options" in result["failed_checks"]


def test_duplicate_options_fail():
    result = validate_question(_mcq(options=["A", "A", "B", "C"], correct_answers=["A"]))
    assert result["status"] == "Failed"
    assert "options_unique" in result["failed_checks"]


@pytest.mark.parametrize("option_count", [1, 6])
def test_mcq_option_count_out_of_range_fails(option_count):
    options = [f"Option {i}" for i in range(option_count)]
    result = validate_question(_mcq(options=options, correct_answers=[options[0]]))
    assert result["status"] == "Failed"
    assert "valid_option_shape" in result["failed_checks"]


def test_true_false_wrong_options_fails():
    question = GeneratedQuestion(
        question_type="TrueFalse",
        question_text="Rust has a garbage collector.",
        options=["Yes", "No"],
        correct_answers=["No"],
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
        correct_answers=["borrow checker"],
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


# --- structural validation: boundaries and whitespace edge cases ---


@pytest.mark.parametrize("option_count", [2, 5])
def test_mcq_option_count_boundaries_pass(option_count):
    options = [f"Option {i}" for i in range(option_count)]
    result = validate_question(_mcq(options=options, correct_answers=[options[0]]))
    assert result["status"] == "Passed"


def test_mcq_answer_with_trailing_whitespace_still_matches_option():
    # A stray trailing space on the model's stated answer shouldn't fail an
    # otherwise-correct question.
    result = validate_question(_mcq(correct_answers=["Ownership rules "]))
    assert result["status"] == "Passed"


def test_mcq_answer_with_leading_whitespace_still_matches_option():
    result = validate_question(_mcq(correct_answers=["  Ownership rules"]))
    assert result["status"] == "Passed"


def test_true_false_lowercase_options_fail():
    # Case sensitivity is intentional — the schema expects exactly "True"/"False".
    question = GeneratedQuestion(
        question_type="TrueFalse",
        question_text="Rust has a garbage collector.",
        options=["true", "false"],
        correct_answers=["false"],
        explanation="Rust uses ownership and borrowing instead of a garbage collector.",
        estimated_time_seconds=15,
        tags=[],
    )
    result = validate_question(question)
    assert result["status"] == "Failed"
    assert "valid_option_shape" in result["failed_checks"]


def test_fill_in_blank_whitespace_only_answer_fails():
    question = GeneratedQuestion(
        question_type="FillInBlank",
        question_text="The ___ enforces ownership.",
        options=None,
        correct_answers=["   "],
        explanation="This component checks ownership and borrowing rules at compile time.",
        estimated_time_seconds=20,
        tags=[],
    )
    result = validate_question(question)
    assert result["status"] == "Failed"
    assert "answer_in_options" in result["failed_checks"]


def test_explanation_exactly_at_minimum_length_passes():
    exactly_15_chars = "x" * 15
    result = validate_question(_mcq(explanation=exactly_15_chars))
    assert result["status"] == "Passed"


def test_explanation_one_char_under_minimum_is_warning():
    just_under = "x" * 14
    result = validate_question(_mcq(explanation=just_under))
    assert result["status"] == "Warning"
    assert result["failed_checks"] == ["explanation_quality"]


# --- MCQMultiSelect structural validation ---


def test_valid_multi_select_passes():
    result = validate_question(_multi_select())
    assert result["status"] == "Passed"
    assert result["failed_checks"] == []


def test_multi_select_single_correct_answer_fails():
    # A multi-select question with only one correct answer isn't multi-select.
    result = validate_question(_multi_select(correct_answers=["Each value has one owner"]))
    assert result["status"] == "Failed"
    assert "answer_in_options" in result["failed_checks"]


def test_multi_select_all_options_correct_fails():
    # Must keep at least one distractor — otherwise the question is meaningless.
    options = ["A", "B", "C"]
    result = validate_question(_multi_select(options=options, correct_answers=options))
    assert result["status"] == "Failed"
    assert "answer_in_options" in result["failed_checks"]


def test_multi_select_duplicate_correct_answers_fail():
    result = validate_question(
        _multi_select(correct_answers=["Each value has one owner", "Each value has one owner"])
    )
    assert result["status"] == "Failed"
    assert "answer_in_options" in result["failed_checks"]


def test_multi_select_answer_not_in_options_fails():
    result = validate_question(
        _multi_select(correct_answers=["Each value has one owner", "Not a real option"])
    )
    assert result["status"] == "Failed"
    assert "answer_in_options" in result["failed_checks"]


@pytest.mark.parametrize("option_count", [2, 7])
def test_multi_select_option_count_out_of_range_fails(option_count):
    options = [f"Option {i}" for i in range(option_count)]
    result = validate_question(_multi_select(options=options, correct_answers=options[:2]))
    assert result["status"] == "Failed"
    assert "valid_option_shape" in result["failed_checks"]


@pytest.mark.parametrize("option_count", [3, 6])
def test_multi_select_option_count_boundaries_pass(option_count):
    options = [f"Option {i}" for i in range(option_count)]
    result = validate_question(_multi_select(options=options, correct_answers=options[:2]))
    assert result["status"] == "Passed"


def test_multi_select_answers_with_whitespace_still_match_options():
    result = validate_question(
        _multi_select(
            correct_answers=["Each value has one owner ", "  Borrows must not outlive the owner"]
        )
    )
    assert result["status"] == "Passed"


# --- answers_match ---


def test_answers_match_exact_text_for_non_computational():
    assert answers_match(["Ownership rules"], ["Ownership rules"], requires_computation=False)


def test_answers_match_is_case_and_whitespace_insensitive():
    assert answers_match(["  ownership RULES  "], ["Ownership rules"], requires_computation=False)


def test_answers_match_rejects_different_text():
    assert not answers_match(
        ["Garbage collection"], ["Ownership rules"], requires_computation=False
    )


def test_answers_match_tolerates_rounding_for_computational():
    assert answers_match(["548.39 Hz"], ["548 Hz"], requires_computation=True)


def test_answers_match_rejects_wrong_number():
    # The actual bug found in live testing: 544 Hz stated vs 548.4 Hz correct.
    assert not answers_match(["548.4 Hz"], ["544 Hz"], requires_computation=True)


def test_answers_match_fails_closed_when_unparsable():
    assert not answers_match(["not a number"], ["544 Hz"], requires_computation=True)


def test_answers_match_fails_closed_when_both_sides_unparsable():
    assert not answers_match(["no idea"], ["also no idea"], requires_computation=True)


def test_answers_match_falls_back_to_text_when_computation_flag_is_a_judge_mistake():
    # Documented in docs/architecture/mistral-api-strategy.md §3: the judge can
    # mis-flag requires_computation=true for a qualitative answer that has no
    # extractable number ("It halves", "True", "O(n log n)") — comparing as
    # normalized text instead of failing outright avoids silently dropping an
    # otherwise-correct question.
    assert answers_match(["It halves"], ["It halves"], requires_computation=True)
    assert answers_match(["O(n log n)"], ["o(n log n)."], requires_computation=True)


def test_answers_match_handles_negative_numbers():
    assert answers_match(["-5 degrees"], ["-5 degrees"], requires_computation=True)


def test_answers_match_rejects_wrong_sign():
    assert not answers_match(["-5 degrees"], ["5 degrees"], requires_computation=True)


def test_answers_match_zero_uses_absolute_not_relative_tolerance():
    # A relative-tolerance check would divide by zero here.
    assert answers_match(["0 m/s"], ["0 m/s"], requires_computation=True)


def test_answers_match_zero_vs_nonzero_does_not_match():
    assert not answers_match(["0.5 m/s"], ["0 m/s"], requires_computation=True)


def test_answers_match_tolerates_thousands_separator():
    assert answers_match(["1000 Hz"], ["1,000 Hz"], requires_computation=True)


def test_answers_match_handles_scientific_notation():
    assert answers_match(["3e8 m/s"], ["300000000 m/s"], requires_computation=True)


def test_answers_match_scientific_notation_rejects_wrong_value():
    assert not answers_match(["3e8 m/s"], ["3e7 m/s"], requires_computation=True)


def test_answers_match_text_ignores_trailing_period():
    assert answers_match(["False."], ["False"], requires_computation=False)


def test_answers_match_text_ignores_trailing_punctuation_on_both_sides():
    assert answers_match(["relative motion!"], ["relative motion?"], requires_computation=False)


def test_answers_match_first_number_wins_when_multiple_present():
    # Documents current behavior: extraction takes the first number found, so
    # a well-formed terse derived answer (as Prompt 4 asks for) works, but an
    # answer string with earlier context/setup numbers ahead of the real
    # answer is a known limitation, not something this function resolves.
    assert not answers_match(
        ["using 340 m/s, the result is 548 Hz"], ["548 Hz"], requires_computation=True
    )


# --- answers_match: multi-select (set comparison) ---


def test_answers_match_multi_select_same_set_different_order():
    assert answers_match(["A", "B"], ["B", "A"], requires_computation=False)


def test_answers_match_multi_select_missing_one_fails():
    assert not answers_match(["A"], ["A", "B"], requires_computation=False)


def test_answers_match_multi_select_extra_one_fails():
    assert not answers_match(["A", "B", "C"], ["A", "B"], requires_computation=False)


def test_answers_match_multi_select_case_and_whitespace_insensitive():
    assert answers_match(["  a", "B "], ["A", "b"], requires_computation=False)


def test_answers_match_requires_computation_rejects_multiple_answers():
    # A computational question only ever has one numeric result — if either
    # side has more than one entry, something is structurally wrong, so this
    # fails closed rather than guessing which entry to compare.
    assert not answers_match(["548 Hz", "549 Hz"], ["548 Hz"], requires_computation=True)


# --- merge_judge_verdict ---


def _verdict(
    requires_computation: bool = False,
    derived_answers: list[str] | None = None,
    **overrides: bool,
) -> JudgeVerdict:
    defaults = {"bloom_aligned": True, "concept_relevant": True}
    return JudgeVerdict(
        index=0,
        requires_computation=requires_computation,
        derived_answers=derived_answers if derived_answers is not None else ["Ownership rules"],
        notes="",
        **{**defaults, **overrides},
    )


def test_merge_judge_verdict_passes_through_when_all_true():
    result = validate_question(_mcq())
    merged = merge_judge_verdict(result, _mcq(), _verdict())
    assert merged == result


def test_merge_judge_verdict_fails_on_wrong_answer():
    result = validate_question(_mcq())
    merged = merge_judge_verdict(result, _mcq(), _verdict(derived_answers=["Garbage collection"]))
    assert merged["status"] == "Failed"
    assert "answer_correct" in merged["failed_checks"]


def test_merge_judge_verdict_fails_on_bloom_misalignment():
    result = validate_question(_mcq())
    merged = merge_judge_verdict(result, _mcq(), _verdict(bloom_aligned=False))
    assert merged["status"] == "Failed"
    assert "bloom_aligned" in merged["failed_checks"]


def test_merge_judge_verdict_fails_on_concept_irrelevance():
    result = validate_question(_mcq())
    merged = merge_judge_verdict(result, _mcq(), _verdict(concept_relevant=False))
    assert merged["status"] == "Failed"
    assert "concept_relevant" in merged["failed_checks"]


def test_merge_judge_verdict_combines_with_prior_warning():
    result = validate_question(_mcq(explanation="Because."))
    assert result["status"] == "Warning"
    merged = merge_judge_verdict(
        result,
        _mcq(explanation="Because."),
        _verdict(derived_answers=["Garbage collection"]),
    )
    assert merged["status"] == "Failed"
    assert merged["failed_checks"] == ["explanation_quality", "answer_correct"]


def test_merge_judge_verdict_reports_every_failed_check_simultaneously():
    result = validate_question(_mcq())
    merged = merge_judge_verdict(
        result,
        _mcq(),
        _verdict(
            derived_answers=["Garbage collection"],
            bloom_aligned=False,
            concept_relevant=False,
        ),
    )
    assert merged["status"] == "Failed"
    assert merged["failed_checks"] == ["answer_correct", "bloom_aligned", "concept_relevant"]


def test_merge_judge_verdict_computational_answer_within_tolerance_passes():
    question = GeneratedQuestion(
        question_type="FillInBlank",
        question_text="What frequency is heard?",
        options=None,
        correct_answers=["548 Hz"],
        explanation="500 * 340 / (340 - 30) = 548.4 Hz",
        estimated_time_seconds=30,
        tags=[],
    )
    result = validate_question(question)
    merged = merge_judge_verdict(
        result,
        question,
        _verdict(requires_computation=True, derived_answers=["548.39 Hz"]),
    )
    assert merged["status"] == "Passed"


def test_merge_judge_verdict_multi_select_passes_when_sets_match_regardless_of_order():
    question = _multi_select()
    result = validate_question(question)
    merged = merge_judge_verdict(
        result,
        question,
        _verdict(
            derived_answers=["Borrows must not outlive the owner", "Each value has one owner"]
        ),
    )
    assert merged["status"] == "Passed"


def test_merge_judge_verdict_multi_select_fails_when_judge_finds_fewer_answers():
    question = _multi_select()
    result = validate_question(question)
    merged = merge_judge_verdict(
        result, question, _verdict(derived_answers=["Each value has one owner"])
    )
    assert merged["status"] == "Failed"
    assert "answer_correct" in merged["failed_checks"]
