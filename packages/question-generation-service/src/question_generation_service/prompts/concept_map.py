from mistralai.client.models import ResponseFormat
from mistralai.client.models.jsonschema import JSONSchema

from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.core.config import get_settings

BLOOM_LEVELS = [
    "Remembering",
    "Understanding",
    "Applying",
    "Analyzing",
    "Evaluating",
    "Creating",
]

COMPLEXITY_LEVELS = ["Low", "Medium", "High"]

PROMPT_2_SYSTEM = """
You are an educational content expert. Given a learning THEMA and its TOPICS, decompose
the subject into atomic, independently-learnable CONCEPTS and for each one produce the
metadata needed to build a quiz.

For each concept output:
- "topic": which of the provided TOPICS this concept belongs to (exact string match)
- "concept": concise, unambiguous name for one atomic learnable unit (Title Case, ≤ 10 words)
- "learning_goal": one clear sentence starting with an action verb describing what the
  learner will be able to do (e.g. "Explain how X works", "Apply Y to solve Z")
- "bloom_levels": ordered list of Bloom levels at which this concept can be meaningfully
  assessed, from lowest to highest applicable level
- "estimated_time_minutes": integer — realistic time in minutes for an average learner to
  grasp this concept (5–120)
- "complexity_level": one of "Low" / "Medium" / "High"
  Low  = recall / definition (Remembering, Understanding)
  Medium = procedural / application (Applying, Analyzing)
  High = design / judgment (Evaluating, Creating)

BLOOM LEVELS (use exact strings):
Remembering | Understanding | Applying | Analyzing | Evaluating | Creating

RULES:
1. Each concept must be atomic — one clear thing to learn, not a topic summary.
2. Concepts must be distinct and non-overlapping.
3. Every topic in the TOPICS list must have at least one concept.
4. Assign only Bloom levels that are pedagogically meaningful for the concept.
5. Complexity level must be consistent with the assigned Bloom levels.
6. If LEARNER CONTEXT is provided, bias toward concepts appropriate for that learner's level.

OUTPUT: strict JSON only — no explanation, no markdown, no extra text.
"""

PROMPT_2_CONFIG = CompletionConfig(
    model=get_settings().MISTRAL_MODEL,
    temperature=0.2,
    max_tokens=4096,
    n=1,
    response_format=ResponseFormat(
        type="json_schema",
        json_schema=JSONSchema(
            name="concept_map",
            strict=True,
            schema_definition={
                "type": "object",
                "properties": {
                    "concepts": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "topic": {"type": "string"},
                                "concept": {"type": "string"},
                                "learning_goal": {"type": "string"},
                                "bloom_levels": {
                                    "type": "array",
                                    "items": {
                                        "type": "string",
                                        "enum": BLOOM_LEVELS,
                                    },
                                    "minItems": 1,
                                    "maxItems": 6,
                                },
                                "estimated_time_minutes": {
                                    "type": "integer",
                                    "minimum": 5,
                                    "maximum": 120,
                                },
                                "complexity_level": {
                                    "type": "string",
                                    "enum": COMPLEXITY_LEVELS,
                                },
                            },
                            "required": [
                                "topic",
                                "concept",
                                "learning_goal",
                                "bloom_levels",
                                "estimated_time_minutes",
                                "complexity_level",
                            ],
                            "additionalProperties": False,
                        },
                        "minItems": 1,
                        "maxItems": 50,
                    }
                },
                "required": ["concepts"],
                "additionalProperties": False,
            },
        ),
    ),
)
