# Memosphere AI Prompts

Four LLM prompts drive the quiz-generation pipeline in `question-generation-service`.

**Source of truth is the code** — full system-prompt text, JSON schemas, and model
configs live in `packages/question-generation-service/src/question_generation_service/prompts/`.
This doc describes each prompt's role, contract, and design intent; it deliberately does
not duplicate the prompt text.

## Pipeline

```
User input ─▶ P1 Thema/Topic Extraction ─▶ P2 Concept Mapping ─▶ P3 Question Generation ─▶ P4 Question Judge ─▶ Accepted questions
```

All prompts use Mistral strict structured output (`json_schema`), so response shape is
enforced by the API, not by parsing.

| #   | Name                               | File                             | Called from                    | Temp |
| --- | ---------------------------------- | -------------------------------- | ------------------------------ | ---- |
| 1   | Thema & Topic Extraction           | `prompts/thema_topic_extract.py` | `services/thema_service.py`    | 0.3  |
| 2   | Concept Mapping & Bloom Assignment | `prompts/concept_map.py`         | `services/concept_service.py`  | 0.2  |
| 3   | Question Generation                | `prompts/question_generation.py` | `services/question_service.py` | 0.5  |
| 4   | Question Judge                     | `prompts/question_judge.py`      | `services/question_service.py` | 0.1  |

---

## Prompt 1 — Thema & Topic Extraction

Converts raw learner input (keyword, sentence, learning goal, or pasted content) into a
normalized **Thema**, a **domain**, and 3–7 **Topics**. Seeds everything downstream.

Beyond simple extraction, it also:

- **Classifies the input** (`input_kind`): a real topic vs. greeting/chit-chat, a
  question about the app, or unintelligible input. Non-topic inputs get a
  wizard-persona `reply` instead of a thema.
- **Disambiguates homonyms** ("spring", "if"): returns the best reading plus up to 2
  `alternates`, each with its own domain, disambiguator, confirmation sentence, and
  topics, and a calibrated `confidence` (probability, not enthusiasm).
- **Honors clarifications**: a `CLARIFICATION:` line in the input is the learner's
  correction and is authoritative — it forces one decisive thema (confidence ≥ 0.9,
  no alternates).
- **Treats pasted content bodies as authoritative** over the keyword.

Domains are a fixed taxonomy (`DOMAINS` in the file) so disambiguators stay stable
across requests. See `docs/product/functional/thema-extraction-disambiguation.md` for
the product-level flow.

---

## Prompt 2 — Concept Mapping & Bloom Assignment

Decomposes a confirmed Thema + Topics into atomic, independently learnable
**Concepts** (max 50), each with:

- owning `topic` (exact match against the input list — every topic gets ≥ 1 concept)
- `learning_goal` (action-verb sentence)
- `bloom_levels` — ordered subset of the 6 Bloom levels that are pedagogically
  meaningful for the concept
- `estimated_time_minutes` (5–120)
- `complexity_level` Low/Medium/High, consistent with the Bloom levels

Optionally biased by learner context when provided.

---

## Prompt 3 — Question Generation

Generates a batch of exactly `BATCH_SIZE` (see `schemas/question.py`) questions for one
(concept, Bloom level, difficulty tier) cell.

- System prompt and JSON schema are **built per request**
  (`build_prompt_3_system/config`): the question-type enum is restricted to the
  learner's wizard selection, and the schema enum — not the prose — is what enforces it.
- Supported types: MCQ, MCQMultiSelect, TrueFalse, FillInBlank, with per-type option
  and correct-answer constraints (e.g. multi-select must never mark every option correct).
- Each question carries an explanation, estimated answer time, and tags.
- Guardrails: answerable from concept + learning goal alone, plausible distractors, no
  stem repetition within a batch, no leaking the Bloom level/tier in the text.

---

## Prompt 4 — Question Judge

Independent audit of Prompt 3's drafts before acceptance. The judge receives question
text and options **without the claimed answers**, so it must derive its own from
scratch — nothing to rubber-stamp.

Per question it returns:

- `derived_answers` — its own worked-out answer(s); numeric result for computational
  questions
- `requires_computation`
- `bloom_aligned` / `concept_relevant` — with a short note when false

`question_service` compares the derived answers against the generator's to accept or
reject drafts. Runs on the same model as generation, deliberately: a weaker judge is
unlikely to catch the generator's mistakes. See
`docs/product/functional/question-quality-control-strategy.md` for the QC strategy.

---

## Maintenance

When a prompt changes in code, update only the affected section's description here —
never paste prompt text into this doc.
