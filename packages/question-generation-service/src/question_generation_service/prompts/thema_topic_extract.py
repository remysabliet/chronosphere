from question_generation_service.clients.mistral_config import CompletionConfig

from mistralai.client.models import ResponseFormat
from mistralai.client.models.jsonschema import JSONSchema

PROMPT_1_SYSTEM = """
You are an educational taxonomy expert. Your role is to analyze a learner's raw input and extract a structured learning scope.

Given raw input (a keyword, sentence, or learning goal), output a single JSON object with:
- "thema": The canonical subject domain
- "topics": A list of 3 to 7 distinct subtopics within that thema

NORMALIZATION RULES:
1. Thema — collapse synonyms and rephrasings into one canonical name:
   - "The process of photosynthesis" → "Photosynthesis"
   - "How plants make food" → "Photosynthesis"
   - "JLPT N1 Japanese" → "Japanese Language JLPT N1"
   - Title case, singular form, no punctuation
2. Topics — identify the main learning subdivisions of the thema:
   - Specific enough to guide concept generation in the next step
   - No overlap between topics
   - Ordered from foundational to advanced
3. If the input is ambiguous or very broad, infer the most common learning interpretation
4. Never include topics outside the thema's scope

OUTPUT: strict JSON only — no explanation, no markdown, no extra text.
"""

PROMPT_1_CONFIG = CompletionConfig(
    temperature=0.0,
    max_tokens=512,
    response_format=ResponseFormat(
        type="json_schema",
        json_schema=JSONSchema(
            name="thema_extraction",
            strict=True,
            schema_definition={
                "type": "object",
                "properties": {
                    "thema": {"type": "string"},
                    "topics": {
                        "type": "array",
                        "items": {"type": "string"},
                        "minItems": 3,
                        "maxItems": 7,
                    },
                },
                "required": ["thema", "topics"],
                "additionalProperties": False,
            },
        ),
    ),
)
