# 🎯 Thema Extraction — Context Disambiguation Strategy

## Problem

Short or single-token inputs are ambiguous **by nature**. `"if"` may mean an
`if` statement (Software), an IaC conditional (DevOps), the Excel `IF` function
(Data), or an English conditional (Language). The goal of thema extraction is to
ensure **the learner is questioned on what they expect** — so a wrong-context
thema poisons every downstream question.

### Root cause (current pipeline)

`prompts/thema_topic_extract.py` today:

- forces **exactly one** `thema` + **3–7** `topics`, even for `"if"`;
- runs at `temperature=0.0`, so it deterministically commits to whichever single
  interpretation is most probable _globally_;
- has **no notion of confidence or ambiguity**;
- sees the **bare keyword with zero learner context**.

No prompt tweak fixes this: the disambiguating information isn't in the input,
it's in the context around it. When context can't decide, the system must **ask
once** instead of silently guessing.

The DB model already anticipates this — `models/thema.py` has
`extraction_confidence`, `user_corrected`, `user_correction` (currently unused).

---

## Strategy: context-fusion + confidence-gated disambiguation

Three layers. Resolve automatically when signals exist; ask the user once when
they don't; **always confirm understanding before generating questions** — never
generate on a context the learner hasn't explicitly agreed to.

1. **Context fusion** — extract from the keyword **plus** surrounding signals,
   not the bare keyword.
2. **Self-consistency confidence** — sample the extraction multiple times; the
   spread across interpretations _is_ the ambiguity signal.
3. **Decision gate** — choose the _confirmation UX_: a single confirmation
   sentence for a clear winner, or a ranked "Did you mean…?" picker when
   ambiguous. **Confirmation is unconditional** — even a confident extraction
   requires an explicit user yes.

---

## Decisions (locked)

| Topic                 | Decision                                                                    |
| --------------------- | --------------------------------------------------------------------------- |
| Confirmation          | **Unconditional** — every extraction is confirmed by the user               |
| Confirmation sentence | **LLM-authored** — each sample emits its own `confirmation` (no extra call) |
| Ambiguity UX          | **Ask the user** (return candidates, client picks)                          |
| Confidence mechanism  | **Self-consistency**, `n=5`                                                 |
| API shape             | **Two endpoints** (`extract` + `confirm`)                                   |
| Candidate storage     | **JSON in `notes` column** (no migration)                                   |
| v1 context scope      | **`content_body` only** — `learner_context` stubbed                         |

---

## LLM contract (per sample)

Each sample returns a **single** best interpretation — no self-rated confidence,
no candidate array. Confidence is derived by aggregation, not self-report.

```jsonc
{
  "thema": "Conditional Statements in Programming",
  "domain": "Software", // fixed enum
  "disambiguator": "if control flow",
  "confirmation": "You'll be quizzed on if/else conditional logic in programming — syntax, truthiness, and branching, not loops.",
  "topics": ["...", "..."], // 3–7
}
```

The `confirmation` is the **LLM-authored one-sentence restatement** shown to the
learner. It comes free with each sample — the representative sample of the
winning cluster carries it into the response. For an `ambiguous` result each
candidate keeps its own `confirmation`, so every option is self-describing.

Invoked with **`n=5, temperature=0.7, random_seed=None`** (one request, 5
choices). We trade reproducibility on this short prompt for a real ambiguity
signal.

### `domain` enum (fixed, for stable clustering)

`Software · DevOps · Data · Language · Math · Science · Business · Arts · General`

### Prompt additions

- **Learner-context block** above the input: `content_body` (v1), plus stubbed
  `profession / education / prior_themas` (future fusion phase).
  Rule: _if content body is present it is **authoritative** — the keyword is only
  a lens; never contradict the body._
- **Fixed `domain` enum**.
- **Honest-spread instruction**: read the input naturally per-sample; do not
  force the same interpretation every time.
- **Confirmation sentence**: emit `confirmation` — one plain-language sentence a
  learner can verify at a glance, naming the scope and what's excluded.

---

## Aggregation → confidence

1. Normalize each sample key: title-cased `thema` + `domain`.
2. Group; `confidence = votes / 5`; representative sample carries the topics.
3. Sort desc → candidate list.

## Decision gate (vote-share, quantized to 0.2 at n=5)

The gate selects the **confirmation UX**, never whether to confirm — confirmation
always happens.

```
T_HIGH = 0.6   # ≥3 of 5
MARGIN = 0.4   # ≥2 votes clear of #2

resolved   if top.conf ≥ T_HIGH and (no second or top−second ≥ MARGIN)
              → show single confirmation sentence (Confirm / Edit)
unresolved if top.conf ≤ 0.2 and domains are scattered      # "couldn't identify"
              → ask learner to add a word or two
ambiguous  otherwise → return top 3 candidates, each with its own confirmation
```

`resolved` **does not** auto-proceed: it skips the picker but still requires an
explicit confirm before question generation.

Worked outcomes:

| Vote split  | Result     |
| ----------- | ---------- |
| `5-0`       | resolved   |
| `4-1`       | resolved   |
| `3-1-1`     | resolved   |
| `3-2`       | ambiguous  |
| `2-2-1`     | ambiguous  |
| `1-1-1-1-1` | unresolved |

> Bump `n` to 7/9 later for finer confidence granularity — config only.
> Self-reported LLM confidence at `temp=0` was rejected: poorly calibrated, and
> always _looks_ certain.

---

## API (two endpoints)

### `POST /v1/thema/extract`

Request (context optional — keyword-only path still works):

```jsonc
{
  "raw_user_input": "if",
  "user_id": "uuid|null",
  "session_id": "uuid|null",
  "content_body": "string|null", // pasted text / scraped URL / PDF extract
  "learner_context": {
    // STUB in v1, not fetched cross-service
    "profession": "string|null",
    "education_level": "string|null",
    "prior_themas": [],
  },
}
```

Response — discriminated union on `status`. **No status proceeds to question
generation without a `confirm` call.** `resolved` carries a single `confirmation`
sentence; `ambiguous` carries one per candidate.

```jsonc
// resolved — single confirmation, picker skipped
{ "status": "resolved", "extraction_id": "uuid",
  "thema": "...", "topics": [...], "confidence": 0.8, "domain": "Software",
  "confirmation": "You'll be quizzed on if/else conditional logic in programming." }

// ambiguous — pick one; each is self-describing
{ "status": "ambiguous", "extraction_id": "uuid",
  "candidates": [
    { "rank": 1, "thema": "...", "domain": "Software",
      "disambiguator": "if control flow", "confidence": 0.4, "topics": [...],
      "confirmation": "You'll be quizzed on if/else conditionals in programming." }
  ] }

// unresolved
{ "status": "unresolved", "extraction_id": "uuid" }
```

### `POST /v1/thema/{extraction_id}/confirm`

Mandatory final step for **every** non-`unresolved` extraction.

```jsonc
{ "chosen_rank": 1 } // 1 for a resolved single-candidate; or the picked rank; or a free-text override
```

Returns the `resolved` shape. On `ambiguous` (or override), writes
`user_corrected=true` + `user_correction`; (future) appends to
`user_thema_exposure`. Reject re-confirm on an already-confirmed row.

---

## Persistence (`notes` JSON, no migration)

- **extract** writes a row with `extraction_confidence` and a `status`. Because
  confirmation is unconditional, the extract step is never terminal:
  `pending_confirmation` (clear winner) / `pending_disambiguation` (ambiguous) /
  `unresolved`. Candidate list + confirmation + status serialized as **JSON in
  `notes`**.
- **confirm** → new `update_on_confirm()`: set `status = confirmed`, write
  `extracted_thema/topic`; set `user_corrected`/`user_correction` only when the
  pick differs from the top candidate (ambiguous or free-text override).
- `save()` signature gains `extraction_confidence` + `status`.

Columns already exist in `models/thema.py`.

---

## Worked examples

### `"if"` (no content body)

- Samples scatter: `Software ×2`, `DevOps ×1`, `Language ×2` → top 0.4, margin 0
  → **ambiguous** → ask: _if-statement (coding) / IaC conditional / English
  conditionals?_ User taps → stored.
- _With content body_ mentioning `else`, `boolean`, `return` → 5/5 Software →
  **resolved** silently.

### `"Spring"` (content body: "Bean, @Autowired, dependency injection")

- Body authoritative → 5/5 `Spring Framework (Java)` → **resolved**.
- _Keyword alone_ → `Framework ×2`, `Season ×2`, `Mechanical ×1` → **ambiguous**.

---

## Files touched (v1)

| File                               | Change                                               |
| ---------------------------------- | ---------------------------------------------------- |
| `prompts/thema_topic_extract.py`   | single-interpretation schema + new prompt            |
| `clients/mistral_config.py`        | per-call `n=5`, `temperature=0.7`                    |
| `services/thema_service.py`        | aggregation + decision gate                          |
| `schemas/thema.py`                 | request context + response union                     |
| `routers/thema_router.py`          | add `confirm` endpoint                               |
| `repositories/thema_repository.py` | `status`/`confidence` on save, `update_on_confirm()` |

## Out of scope (later phases)

- Cross-service fetch of `profession / education / prior_themas`
  (`users`, `user_thema_exposure` not owned by this service).
- Feeding confirmations back into `user_thema_exposure`.
- Finer `n`, threshold calibration from real misclassification data.
