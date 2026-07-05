from mistralai.client.models import ResponseFormat
from mistralai.client.models.jsonschema import JSONSchema

from question_generation_service.clients.mistral_config import CompletionConfig
from question_generation_service.core.config import get_settings

# Fixed taxonomy so disambiguators stay stable across requests.
DOMAINS = [
    "Software",
    "DevOps",
    "Data",
    "Language",
    "Math",
    "Science",
    "Business",
    "Arts",
    "General",
]

MAX_ALTERNATES = 2

_INTERPRETATION_SCHEMA = {
    "type": "object",
    "properties": {
        "thema": {"type": "string"},
        "domain": {"type": "string", "enum": DOMAINS},
        "disambiguator": {"type": "string"},
        "confirmation": {"type": "string"},
        "topics": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 3,
            "maxItems": 7,
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
    "required": ["thema", "domain", "disambiguator", "confirmation", "topics", "confidence"],
    "additionalProperties": False,
}

PROMPT_1_SYSTEM = """
You are an educational taxonomy expert. Read the learner's raw input and return your
single most-plausible interpretation of what they want to study, plus your own
self-assessed confidence and, if the input is genuinely ambiguous, up to {max_alternates}
alternate interpretations.

Output a single JSON object with:
- "thema": canonical subject domain (Title Case, singular, no punctuation)
- "domain": exactly one of {domains}
- "disambiguator": <=6 words naming what tells this reading apart from others
- "confirmation": one plain-language sentence a learner can verify at a glance,
  naming the scope and, where useful, what is excluded
- "topics": 3 to 7 distinct, non-overlapping subtopics a learner would expect and
  want to be quizzed on for this thema — see RULE 5, count is not a target
- "confidence": your own honest probability (0.0-1.0) that this is the reading the
  learner actually meant, GIVEN the alternates you also considered — see RULE 7
- "alternates": 0 to {max_alternates} other plausible readings, each with the same
  five fields above (thema/domain/disambiguator/confirmation/topics/confidence) —
  empty array if the input is not genuinely ambiguous

RULES:
1. Collapse synonyms/rephrasings into one canonical thema
   ("how plants make food" -> "Photosynthesis").
2. If a CONTENT BODY is provided it is AUTHORITATIVE: derive the thema from it and
   never contradict it; treat the keyword only as a lens over that body.
3. If LEARNER CONTEXT is provided, use it to bias toward the learner's likely intent.
4. The input may be a homonym spanning several domains (e.g. "if", "spring"). When it
   genuinely is, put your best guess first and the other live readings in "alternates"
   — do not silently pick one and hide that it was a close call.
5. Never include topics outside the chosen thema's scope. 7 is a ceiling, not a
   goal: include a topic only if it is core to the thema and a learner would very
   likely expect to be quizzed on it. Drop niche, overly specific, or tangential
   topics rather than padding the list to reach a higher count — 3 strong topics
   beat 7 where some are filler.
6. If INPUT contains a line starting with "CLARIFICATION:", it is the learner's
   correction to a prior guess and is AUTHORITATIVE over everything before it:
   - Re-scope the thema and topics to match it; drop any topic that no longer
     fits the clarified intent even if it fit the earlier guess.
   - If the clarification names specific things the learner wants covered
     (e.g. "slavery, the Morocco war, and Black emancipation"), turn those named
     things into the topics directly (phrased as proper topic titles) rather
     than substituting a generic curriculum — the learner already told you
     exactly what they want.
   - Commit to ONE decisive thema with confidence >= 0.9 and an empty "alternates" —
     the learner already disambiguated once, so treat the case as closed rather
     than reopening the same ambiguity you would flag for a bare keyword.
7. Calibrate honestly: confidence is a probability, not an enthusiasm score. If two
   readings are both plausible, the top pick's confidence should reflect that split
   (e.g. ~0.5-0.6 each, not 0.9), and you must list the other reading as an alternate.
   Reserve confidence >= 0.85 for cases with no serious competing reading.

OUTPUT: strict JSON only — no explanation, no markdown, no extra text.
""".format(domains=", ".join(DOMAINS), max_alternates=MAX_ALTERNATES)

PROMPT_1_CONFIG = CompletionConfig(
    model=get_settings().MISTRAL_MODEL,
    temperature=0.3,
    max_tokens=1024,
    n=1,
    random_seed=None,
    response_format=ResponseFormat(
        type="json_schema",
        json_schema=JSONSchema(
            name="thema_extraction",
            strict=True,
            schema_definition={
                "type": "object",
                "properties": {
                    **_INTERPRETATION_SCHEMA["properties"],
                    "alternates": {
                        "type": "array",
                        "items": _INTERPRETATION_SCHEMA,
                        "minItems": 0,
                        "maxItems": MAX_ALTERNATES,
                    },
                },
                "required": [*_INTERPRETATION_SCHEMA["required"], "alternates"],
                "additionalProperties": False,
            },
        ),
    ),
)
