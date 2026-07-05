# Python Functions for Memosphere

This file contains Python functions referenced in the main workflow for easy retrieval during development.

## Question Validation Function

```python
def validate_question(question: dict) -> dict:
    """
    Validate a generated question against quality criteria.

    Args:
        question: Dictionary containing question data with keys:
            - question_text: The question stem
            - correct_answer: The correct answer
            - options: List of answer options
            - bloom_level: Bloom taxonomy level
            - difficulty_tier: "easy", "medium" or "hard" (proposed by the LLM)
            - question_type: Type of question (e.g., "4-option MCQ")
            - language: Question language

    Returns:
        dict: Validation result with status, failed_checks, score, and notes
    """
    validation_result = {
        "status": "Passed",
        "failed_checks": [],
        "score": 1.0,
        "notes": []
    }

    # Content checks
    if not is_valid_text(question['question_text']):
        validation_result["failed_checks"].append("Invalid question text")

    if not correct_in_options(question['correct_answer'], question['options']):
        validation_result["failed_checks"].append("Correct answer not in options")

    # Alignment checks
    if not bloom_supported(question['bloom_level'], concept_id):
        validation_result["failed_checks"].append("Bloom level not supported")

    # Technical checks
    if question['difficulty_tier'] not in ('easy', 'medium', 'hard'):
        validation_result["failed_checks"].append("Invalid difficulty tier")

    # Determine final status
    if validation_result["failed_checks"]:
        validation_result["status"] = "Failed"
        validation_result["score"] = 1.0 - (len(validation_result["failed_checks"]) * 0.1)

    return validation_result
```

## BKT Update Function

```python
def update_bkt(P_Ln, P_T, P_G, P_S, response_score, bloom_weight=1.0, skipped=False):
    """
    Updates mastery probability (P_Ln) using Bayesian Knowledge Tracing,
    scaled by Bloom level weight and adjusted for partial credit or skipped responses.

    Parameters:
    - P_Ln: Current mastery probability
    - P_T: Learning rate
    - P_G: Guess rate
    - P_S: Slip rate
    - response_score: 0-1 (1=correct, 0=incorrect, 0.5=partial)
    - bloom_weight: Multiplier based on Bloom level (default=1.0)
    - skipped: True if question skipped

    Returns:
    - Updated mastery probability (float, 0-1)

    Note: bloom_weight parameter comes from the bloom_level_weights table
    """
    if skipped:
        return round(P_Ln, 4)  # No update

    # Observation update
    numerator = P_Ln * ((1 - P_S) * response_score + P_S * (1 - response_score))
    denominator = numerator + (1 - P_Ln) * (P_G * response_score + (1 - P_G) * (1 - response_score))
    P_Ln_given_obs = numerator / denominator

    # Bloom-weighted learning gain
    weighted_gain = (1 - P_Ln_given_obs) * P_T * bloom_weight
    P_Ln_plus_1 = P_Ln_given_obs + weighted_gain

    # Clamp to [0,1]
    P_Ln_plus_1 = min(max(P_Ln_plus_1, 0.0), 1.0)
    return round(P_Ln_plus_1, 4)
```

## Response Score Mapping

All evidence enters `update_bkt()` as a `response_score` in [0, 1] — nothing adjusts P(Ln) directly:

| Evidence                | response_score |
| ----------------------- | -------------- |
| Correct, no hints       | 1.0            |
| Correct with hint(s)    | 0.5            |
| Incorrect               | 0.0            |
| Memocard rating "Easy"  | 1.0            |
| Memocard rating "Good"  | 0.8            |
| Memocard rating "Hard"  | 0.4            |
| Memocard rating "Again" | 0.0            |

Audio replays and multimedia engagement are tracked for personalization but never affect P(Ln).
