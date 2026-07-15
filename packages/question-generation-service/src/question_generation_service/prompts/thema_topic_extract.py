from typing import TypedDict

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

INPUT_KINDS = ["topic", "greeting_or_chitchat", "meta_question", "unintelligible"]

_JsonSchema = dict[str, object]


class _ObjectSchema(TypedDict):
    type: str
    properties: dict[str, _JsonSchema]
    required: list[str]
    additionalProperties: bool


_INTERPRETATION_PROPERTIES: dict[str, _JsonSchema] = {
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
}

_INTERPRETATION_REQUIRED: list[str] = [
    "thema",
    "domain",
    "disambiguator",
    "confirmation",
    "topics",
    "confidence",
]

_INTERPRETATION_SCHEMA: _ObjectSchema = {
    "type": "object",
    "properties": _INTERPRETATION_PROPERTIES,
    "required": _INTERPRETATION_REQUIRED,
    "additionalProperties": False,
}

PROMPT_1_SYSTEM = """
You are an educational taxonomy expert. Read the learner's raw input and return your
single most-plausible interpretation of what they want to study, plus your own
self-assessed confidence and, if the input is genuinely ambiguous, up to {max_alternates}
alternate interpretations.

Output a single JSON object with:
- "input_kind": exactly one of {input_kinds} — see RULE 0
- "reply": for non-"topic" inputs only: ONE short, warm sentence answering the
  learner in character as a friendly quiz wizard — see RULE 0. Empty string ""
  when input_kind is "topic".
- "thema": canonical subject domain (Title Case, singular, no punctuation)
- "domain": exactly one of {domains}
- "disambiguator": <=6 words naming what tells this reading apart from others
- "confirmation": one plain-language sentence a learner can verify at a glance,
  naming the scope; mention exclusions only when they resolve a real ambiguity
  with a competing reading
- "topics": 3 to 7 distinct, non-overlapping subtopics a learner would expect and
  want to be quizzed on for this thema — see RULE 5, count is not a target
- "confidence": your own honest probability (0.0-1.0) that this is the reading the
  learner actually meant, GIVEN the alternates you also considered — see RULE 7
- "alternates": 0 to {max_alternates} other plausible readings, each with the same
  five fields above (thema/domain/disambiguator/confirmation/topics/confidence) —
  empty array if the input is not genuinely ambiguous

RULES:
0. FIRST decide whether the input actually describes something to learn.
   Messages addressed to YOU are not study topics: greetings and small talk
   ("hey", "hello", "thanks", "how are you") -> "greeting_or_chitchat";
   questions about the assistant or the app ("what can you do?") -> "meta_question";
   random characters or empty noise -> "unintelligible".
   A bare greeting word is chit-chat BY DEFAULT — treat greeting words as a topic
   only when the message makes the learning intent explicit ("teach me greetings",
   "how to say hello in Spanish").
   If the input contains a "CLARIFICATION:" line, judge input_kind from the LATEST
   CLARIFICATION line alone — a topic-like clarification after a greeting or
   chit-chat opener ("hey" then "python basics") IS a topic.
   For any non-"topic" input_kind: set thema "None", domain "General",
   disambiguator "", confirmation "", topics [], confidence 0, alternates [],
   and write "reply" as a natural response to what they actually said:
   - a greeting -> greet back briefly and invite a subject
   - "let me think" / "give me a sec" -> acknowledge, no rush, you'll be here
   - thanks/appreciation -> you're welcome, offer to keep going
   - a question about you or the app -> answer it in one sentence (you turn any
     subject or pasted text into an adaptive quiz), then invite a subject
   - unintelligible -> gently say you didn't catch that and ask for a subject
   Write the reply fresh for the specific message — never a stock sentence.
   Only when input_kind is "topic" do the rules below apply.
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
   - If a "PRIOR GUESS" block is present, it is the interpretation the learner
     was shown and is reacting to. Keep the prior thema title, scope, and
     difficulty level, and never regenerate the topic list from scratch for a
     mere edit. Apply the clarification as the smallest possible edit:
     * Exclusion ("drop X", "I don't care about X"): return the prior topics
       with ONLY the topics matching the named item(s) removed — every other
       prior topic must reappear word-for-word, including ones the
       clarification never mentioned. If nothing in the prior list matches
       the excluded item, return the prior topics completely unchanged.
     * Addition ("also cover Y"): the requested new topic Y MUST appear in the
       output — this is non-negotiable. Keep every prior topic word-for-word
       and append Y. If the prior list already has 7 topics, you MUST make room
       by merging the two most closely related PRIOR topics into a single topic
       (e.g. "Battles in Europe" + "Battles in the Pacific" -> "Major battles in
       Europe and the Pacific") and keep the rest verbatim — never respond by
       silently dropping Y or leaving the list unchanged.
     * Narrowing ("only X", "just X"): the learner is re-scoping the thema to
       X itself — zoom in: make X (or its direct subtopics) the new scope and
       do not keep prior topics outside X.
     Re-scope the whole thema only for narrowing or when the clarification
     contradicts the prior reading itself.
   - Re-scope the thema and topics to match it; drop any topic that no longer
     fits the clarified intent even if it fit the earlier guess.
   - If the clarification names specific things the learner wants covered
     (e.g. "slavery, the Morocco war, and Black emancipation"), turn those named
     things into the topics directly — EXACTLY ONE topic per named thing, phrased
     as a proper topic title, no more — rather than substituting a generic
     curriculum or expanding each into subtopics. The learner already told you
     exactly what they want and how granular they want it.
   - Commit to ONE decisive thema with confidence >= 0.9 and an empty "alternates" —
     the learner already disambiguated once, so treat the case as closed rather
     than reopening the same ambiguity you would flag for a bare keyword.
   - EXCEPTION: if the CLARIFICATION line is itself a greeting or chit-chat rather
     than a topic-like correction, classify it per RULE 0 (input_kind) instead of
     forcing a decisive thema.
7. Calibrate honestly: confidence is a probability, not an enthusiasm score. If two
   readings are both plausible, the top pick's confidence should reflect that split
   (e.g. ~0.5-0.6 each, not 0.9), and you must list the other reading as an alternate.
   Reserve confidence >= 0.85 for cases with no serious competing reading.

OUTPUT: strict JSON only — no explanation, no markdown, no extra text.
""".format(
    domains=", ".join(DOMAINS),
    max_alternates=MAX_ALTERNATES,
    input_kinds=", ".join(f'"{k}"' for k in INPUT_KINDS),
)

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
                    **_INTERPRETATION_PROPERTIES,
                    "input_kind": {"type": "string", "enum": INPUT_KINDS},
                    "reply": {"type": "string"},
                    # Non-topic inputs return an empty topics list; alternates keep
                    # the 3-item floor since they are always real interpretations.
                    "topics": {
                        **_INTERPRETATION_PROPERTIES["topics"],
                        "minItems": 0,
                    },
                    "alternates": {
                        "type": "array",
                        "items": _INTERPRETATION_SCHEMA,
                        "minItems": 0,
                        "maxItems": MAX_ALTERNATES,
                    },
                },
                "required": [
                    *_INTERPRETATION_REQUIRED,
                    "input_kind",
                    "reply",
                    "alternates",
                ],
                "additionalProperties": False,
            },
        ),
    ),
)
