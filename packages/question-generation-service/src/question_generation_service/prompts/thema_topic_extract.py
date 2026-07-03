from question_generation_service.clients.mistral_config import CompletionConfig

from mistralai.client.models import ResponseFormat
from mistralai.client.models.jsonschema import JSONSchema

# Fixed taxonomy so disambiguators and self-consistency clustering stay stable.
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

SELF_CONSISTENCY_SAMPLES = 5

PROMPT_1_SYSTEM = """
You are an educational taxonomy expert. Read the learner's raw input and return
ONE most-plausible interpretation of what they want to study.

Output a single JSON object with:
- "thema": canonical subject domain (Title Case, singular, no punctuation)
- "domain": exactly one of {domains}
- "disambiguator": <=6 words naming what tells this reading apart from others
- "confirmation": one plain-language sentence a learner can verify at a glance,
  naming the scope and, where useful, what is excluded
- "topics": 3 to 7 distinct, non-overlapping subtopics a learner would expect and
  want to be quizzed on for this thema — see RULE 5, count is not a target

RULES:
1. Collapse synonyms/rephrasings into one canonical thema
   ("how plants make food" -> "Photosynthesis").
2. If a CONTENT BODY is provided it is AUTHORITATIVE: derive the thema from it and
   never contradict it; treat the keyword only as a lens over that body.
3. If LEARNER CONTEXT is provided, use it to bias toward the learner's likely intent.
4. The input may be a homonym spanning several domains (e.g. "if", "spring").
   Read it naturally for THIS sample; do not force a fixed reading across samples —
   pick the interpretation that is genuinely most plausible given the context.
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
   - Commit to ONE decisive thema name and do not hedge: the learner already
     disambiguated once, so do not vary the thema label across re-reads of an
     already-clarified input the way you would for a genuinely ambiguous bare
     keyword — paraphrasing the same answer differently each time looks like
     disagreement and forces the learner to re-disambiguate for no reason.

OUTPUT: strict JSON only — no explanation, no markdown, no extra text.
""".format(domains=", ".join(DOMAINS))

PROMPT_1_CONFIG = CompletionConfig(
    temperature=0.7,
    max_tokens=512,
    n=SELF_CONSISTENCY_SAMPLES,
    random_seed=None,
    response_format=ResponseFormat(
        type="json_schema",
        json_schema=JSONSchema(
            name="thema_extraction",
            strict=True,
            schema_definition={
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
                },
                "required": ["thema", "domain", "disambiguator", "confirmation", "topics"],
                "additionalProperties": False,
            },
        ),
    ),
)
