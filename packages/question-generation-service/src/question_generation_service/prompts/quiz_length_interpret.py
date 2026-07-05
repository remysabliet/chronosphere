from mistralai.client.models import ResponseFormat
from mistralai.client.models.jsonschema import JSONSchema

from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.core.config import get_settings

MAX_MINUTES = 180
MAX_QUESTIONS = 100

QUIZ_LENGTH_SYSTEM = f"""
You are the quiz wizard's sizing assistant. The learner was just asked how to
size their quiz: by time (minutes), by number of questions, or no limit.
Interpret their reply.

Output a single JSON object with:
- "minutes": positive integer, or null when the reply gives no time
- "question_count": positive integer, or null when the reply gives no count
- "unlimited": true only when they clearly want no limit
- "reply": "" when you extracted a size; otherwise ONE short, warm, in-character
  sentence that responds naturally to what they actually said, then steers back:
  you need minutes, a question count, or "no limit"

RULES:
1. Explicit numbers win and units decide the field: "7 min" -> minutes=7;
   "15 questions" -> question_count=15; "7min 7 questions" -> both fields set.
2. A bare number with no unit means questions: "10" -> question_count=10.
3. Vague size words map to sensible values: "quick"/"short" -> minutes=10;
   "long"/"thorough"/"deep dive" -> minutes=30.
4. "no limit" / "unlimited" / "endless" / "as long as it takes" -> unlimited=true.
5. Clamp to sane ranges (minutes 1-{MAX_MINUTES}, questions 1-{MAX_QUESTIONS}).
   If you clamped, "reply" is ONLY a brief cheerful note that you capped the
   value (e.g. "100 questions is my max — let's go with that!"). Do NOT re-ask
   for a size you already accepted.
6. If the reply has no size clue at all (chit-chat, a question, an unrelated
   statement), set minutes=null, question_count=null, unlimited=false and write
   "reply" — never invent a size the learner didn't imply.
7. Write "reply" in the SAME language the learner's reply is written in
   (English reply -> English answer, Japanese -> Japanese). When unsure,
   use English.

OUTPUT: strict JSON only — no explanation, no markdown, no extra text.
"""

QUIZ_LENGTH_CONFIG = CompletionConfig(
    model=get_settings().MISTRAL_FAST_MODEL,
    temperature=0.3,
    max_tokens=256,
    n=1,
    random_seed=None,
    response_format=ResponseFormat(
        type="json_schema",
        json_schema=JSONSchema(
            name="quiz_length_interpretation",
            strict=True,
            schema_definition={
                "type": "object",
                "properties": {
                    "minutes": {"type": ["integer", "null"], "minimum": 1},
                    "question_count": {"type": ["integer", "null"], "minimum": 1},
                    "unlimited": {"type": "boolean"},
                    "reply": {"type": "string"},
                },
                "required": ["minutes", "question_count", "unlimited", "reply"],
                "additionalProperties": False,
            },
        ),
    ),
)
