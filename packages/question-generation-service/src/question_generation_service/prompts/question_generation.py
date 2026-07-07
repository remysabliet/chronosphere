from collections.abc import Sequence

from mistralai.client.models import ResponseFormat
from mistralai.client.models.jsonschema import JSONSchema

from memosphere_domain import QuestionType
from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.core.config import get_settings
from question_generation_service.schemas.question import BATCH_SIZE


def build_prompt_3_system(allowed_types: Sequence[QuestionType]) -> str:
    """Builds Prompt 3's system message, restricted to `allowed_types` — the
    learner's chosen question type(s) from the wizard. The enum restriction in
    `build_prompt_3_config`'s JSON schema is what actually enforces this (via
    Mistral's strict structured-output mode); this text just explains the rules
    for whichever types are in play.
    """
    types_list = ", ".join(f'"{t}"' for t in allowed_types)
    return f"""
You are an expert quiz item writer. Given a CONCEPT, its LEARNING GOAL, a target
BLOOM LEVEL, and a target DIFFICULTY TIER, generate exactly {BATCH_SIZE} quiz
questions that assess the concept at exactly that Bloom level and tier.

For each question output:
- "question_type": one of {types_list}
- "question_text": the question stem, self-contained, no reference to "the above".
  For MCQMultiSelect, tell the learner more than one option is correct.
- "options": array of 2-5 answer options for MCQ, 3-6 for MCQMultiSelect,
  exactly ["True", "False"] for TrueFalse, or null for FillInBlank
- "correct_answers": array of the exact text of every correct option
  (MCQ/TrueFalse: exactly 1 entry; MCQMultiSelect: 2 or more entries, and
  strictly fewer than the number of options — never mark every option
  correct; FillInBlank: exactly 1 entry, the missing word/phrase) — every
  entry must appear verbatim in "options" when options is set
- "explanation": one or two sentences explaining why the answer(s) are
  correct, useful on its own as a learning moment
- "estimated_time_seconds": realistic time to answer (5-300)
- "tags": short lowercase keywords for this question (0-5)

BLOOM LEVEL GUIDANCE (write questions that genuinely require this cognitive
skill, not just recall dressed up as the target level):
- Remembering: recall a fact, term, or definition
- Understanding: explain or restate in own words, interpret
- Applying: use the concept in a new, concrete situation
- Analyzing: break down, compare, find relationships or causes
- Evaluating: judge, critique, justify a choice against criteria
- Creating: design, propose, or synthesize something new using the concept

DIFFICULTY TIER GUIDANCE:
- easy: single-step, unambiguous, common case
- medium: multi-step or requires combining two ideas
- hard: edge cases, subtle distractors, or multi-concept reasoning

RULES:
1. Every question must be answerable from the CONCEPT and LEARNING GOAL alone —
   no outside trivia.
2. Distractors (wrong options) must be plausible, not silly or obviously wrong.
3. Never repeat the same question stem or scenario within the batch.
4. Do not leak the Bloom level or difficulty tier in the question text.

OUTPUT: strict JSON only — no explanation, no markdown, no extra text.
"""


def build_prompt_3_config(allowed_types: Sequence[QuestionType]) -> CompletionConfig:
    return CompletionConfig(
        model=get_settings().MISTRAL_MODEL,
        temperature=0.5,
        max_tokens=4096,
        n=1,
        response_format=ResponseFormat(
            type="json_schema",
            json_schema=JSONSchema(
                name="question_batch",
                strict=True,
                schema_definition={
                    "type": "object",
                    "properties": {
                        "questions": {
                            "type": "array",
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question_type": {
                                        "type": "string",
                                        "enum": list(allowed_types),
                                    },
                                    "question_text": {"type": "string"},
                                    "options": {
                                        "type": ["array", "null"],
                                        "items": {"type": "string"},
                                    },
                                    "correct_answers": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "minItems": 1,
                                    },
                                    "explanation": {"type": "string"},
                                    "estimated_time_seconds": {
                                        "type": "integer",
                                        "minimum": 5,
                                        "maximum": 300,
                                    },
                                    "tags": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                                "required": [
                                    "question_type",
                                    "question_text",
                                    "options",
                                    "correct_answers",
                                    "explanation",
                                    "estimated_time_seconds",
                                    "tags",
                                ],
                                "additionalProperties": False,
                            },
                            "minItems": BATCH_SIZE,
                            "maxItems": BATCH_SIZE,
                        }
                    },
                    "required": ["questions"],
                    "additionalProperties": False,
                },
            ),
        ),
    )
