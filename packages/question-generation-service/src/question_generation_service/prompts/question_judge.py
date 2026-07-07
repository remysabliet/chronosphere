from mistralai.client.models import ResponseFormat
from mistralai.client.models.jsonschema import JSONSchema

from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.core.config import get_settings

PROMPT_4_SYSTEM = """
You are a rigorous quiz question auditor. You will be given a CONCEPT, its
LEARNING GOAL, a target BLOOM LEVEL, and a batch of already-generated quiz
questions — question text and options only, with NO stated answer attached.

For each question, work out your OWN answer(s) from scratch, as if you were a
learner answering it. You have not been told what the original generator
claimed was correct, so there is nothing to rubber-stamp — you must actually
derive it. Some questions accept more than one correct option (you'll see
this from the question text itself) — for those, derive every correct one.

For each question return:
1. "requires_computation": true if answering requires an actual calculation
   (arithmetic, a formula, a unit conversion, etc.); false if it's purely
   conceptual/definitional/recall.
2. "derived_answers": array of YOUR OWN worked-out answer(s) — one entry for
   an ordinary question, two or more entries only if the question genuinely
   accepts multiple correct options. For computational questions, give the
   final numeric result (with units if relevant) — show the number, not just
   the method. For conceptual questions, state the answer itself (e.g. the
   correct option's text, or True/False, or the missing word).
3. "bloom_aligned": does the question's actual cognitive demand genuinely
   match the stated BLOOM LEVEL — not noticeably easier or harder than that
   level implies?
4. "concept_relevant": does the question genuinely assess the stated CONCEPT
   and LEARNING GOAL, not something tangential?

For each question return an object with "index" (the question's index from
the input, unchanged), "requires_computation", "derived_answers",
"bloom_aligned", "concept_relevant", and "notes" (empty string unless
bloom_aligned or concept_relevant is false, then one short sentence on what's
wrong).

Return one verdict per question, in any order — "index" is what maps it back.

OUTPUT: strict JSON only — no explanation, no markdown, no extra text.
"""

PROMPT_4_CONFIG = CompletionConfig(
    # Same large model as generation, deliberately: a judge no more capable
    # than the generator is unlikely to catch the generator's own mistakes.
    model=get_settings().MISTRAL_MODEL,
    temperature=0.1,
    max_tokens=2048,
    n=1,
    response_format=ResponseFormat(
        type="json_schema",
        json_schema=JSONSchema(
            name="question_judge_verdicts",
            strict=True,
            schema_definition={
                "type": "object",
                "properties": {
                    "verdicts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "index": {"type": "integer"},
                                "requires_computation": {"type": "boolean"},
                                "derived_answers": {
                                    "type": "array",
                                    "items": {"type": "string"},
                                    "minItems": 1,
                                },
                                "bloom_aligned": {"type": "boolean"},
                                "concept_relevant": {"type": "boolean"},
                                "notes": {"type": "string"},
                            },
                            "required": [
                                "index",
                                "requires_computation",
                                "derived_answers",
                                "bloom_aligned",
                                "concept_relevant",
                                "notes",
                            ],
                            "additionalProperties": False,
                        },
                    }
                },
                "required": ["verdicts"],
                "additionalProperties": False,
            },
        ),
    ),
)
