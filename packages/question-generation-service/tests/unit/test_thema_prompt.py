"""Guards the load-bearing clauses of Prompt 1's clarification rules. These
back the wizard-refinement edge cases exercised live in scripts/wizard_sim.py;
this keeps the behavior from silently regressing if the prompt is edited.
"""

from question_generation_service.prompts.thema_topic_extract import (
    _INTERPRETATION_SCHEMA,
    PROMPT_1_SYSTEM,
)


def test_prompt_documents_prior_guess_handling():
    assert "PRIOR GUESS" in PROMPT_1_SYSTEM


def test_prompt_covers_each_clarification_edit_kind():
    prompt = PROMPT_1_SYSTEM.lower()
    # Exclusion keeps the untouched topics verbatim.
    assert "exclusion" in prompt
    assert "word-for-word" in prompt or "verbatim" in prompt
    # Addition is non-negotiable and merges at the ceiling.
    assert "addition" in prompt
    assert "merg" in prompt
    # Narrowing re-scopes rather than filters.
    assert "narrowing" in prompt


def test_prompt_judges_input_kind_from_latest_clarification():
    assert "CLARIFICATION" in PROMPT_1_SYSTEM
    assert "input_kind" in PROMPT_1_SYSTEM


def test_interpretation_schema_bounds_topic_count():
    topics = _INTERPRETATION_SCHEMA["properties"]["topics"]
    assert topics["minItems"] == 3
    assert topics["maxItems"] == 7
