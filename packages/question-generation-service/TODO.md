# Question Generation Service – Implementation Plan

This document describes what needs to be developed for the `question-generation-service` (FastAPI + Mistral) and how it should be structured.

---

## 1. Service Responsibilities (High-Level)

The service is responsible for:

1. **Thema & Concept Analysis** — DONE
   - Turn raw user text into a normalized `thema` + `topics` (Prompt 1).
   - Map thema/topics to atomic concept–Bloom pairs (Prompt 2), reusing
     already-mapped concepts for a thema instead of re-generating them —
     Prompt 1 canonicalizes thema/topic text, so the same real-world subject
     always produces the same strings across different users.

2. **Exposure Check & BKT Initialization** — DONE
   - Look up prior exposure for (user, thema); if unknown, ask the learner
     and seed P(L0) accordingly.
   - Initialize `concept_progress_tracker` (P(Ln) = P(L0)) per concept–Bloom
     pair once exposure is known (`main-workflow.md` Steps 5 & 7).

3. **Question Generation & Validation** — DONE
   - Generate a batch of questions per concept–Bloom–tier bucket using
     Mistral (Prompt 3), shared across every learner who reaches that bucket
     (no `user_id`/`session_id` on `questions` — see main-workflow.md Step 8).
   - Deterministic structural validation (options well-formed, answer present,
     etc.) plus an independent LLM judge (Prompt 4) that re-derives its own
     answer and checks Bloom/concept alignment, rather than trusting the
     generator's self-reported correctness.
   - Log every validation outcome — passed, warned, and dropped — to
     `question_validation_log`.

4. **Question Retrieval & Feedback** — NOT STARTED
   - Provide read access to stored questions (e.g. `GET /v1/questions/{id}`
     for `quiz-session-service` to fetch by ID).
   - Accept user feedback (ratings, flags) for quality improvement.

5. **Moderation & Quality Monitoring** — NOT STARTED
   - Expose lists of flagged/failed questions for moderators.
   - Allow moderators to change question status (approved/rejected/disabled).

---

## 2. API Design

### 2.1 Health

- **GET `/health`**
  - **Purpose**: Liveness/readiness for Docker / NGINX / k8s.
  - **Response**:  
    `{ "status": "ok", "service": "question-generation" }`

---

### 2.2 Thema, Concept, and Exposure — DONE (actual shapes below)

- **POST `/v1/thema/extract`** (Prompt 1)
  - **Request**: `{ "raw_user_input": "string", "content_body": "string?", "learner_context": {...}? }`
  - **Response**: one of `ResolvedThema` / `AmbiguousThema` / `UnresolvedThema` / `NonTopicInput`
    (discriminated by `status`) — see `schemas/thema.py`.

- **POST `/v1/thema/{id}/refine`**
  - **Purpose**: Re-interpret with a learner clarification when the first extraction
    was ambiguous/unresolved. Same response union as `extract`.

- **POST `/v1/thema/{id}/confirm`**
  - **Purpose**: Lock in the resolved thema. Internally, in one call: maps concepts
    for any topic not already mapped for this thema (Prompt 2 — reuses existing
    `learning_units` rows for topics someone already mapped), then checks
    `user_thema_exposure` for this user+thema.
  - **Response**: `ResolvedThema`, with `exposure_required: bool` — true means the
    client must ask the learner and call the exposure endpoint below before BKT
    is initialized.

- **POST `/v1/thema/{id}/exposure`**
  - **Purpose**: Submit the learner's self-reported exposure level
    (`Unseen`/`Recognized`/`Practiced`/`Mastered`) when `confirm()` didn't already
    have one on file. Seeds P(L0) and initializes `concept_progress_tracker` for
    every concept–Bloom pair under that thema (Step 7).
  - **Response**: `ExposureResult` (`thema`, `exposure_level`, `p_l0`, `concepts_initialized`).

- **POST `/v1/concepts/map`** (Prompt 2)
  - Standalone/admin entry point to the same concept mapper `confirm()` calls
    internally — useful for re-mapping or moderation tooling, not part of the
    normal learner flow.

---

### 2.3 Question Generation & Validation — mostly DONE, retrieval still missing

- **POST `/v1/questions/generate`** — DONE (Prompt 3 + Step 8A + Prompt 4 judge, store, return)
  - **Purpose**: Generate one batch (`BATCH_SIZE = 5`) of questions for a single
    concept–Bloom–tier bucket, run structural validation, then run an independent
    judge pass on the survivors (re-derives its own answer, checks Bloom/concept
    alignment — never shown the draft's stated answer), store only what passes
    both, and log every outcome (including dropped drafts, `question_id = NULL`)
    to `question_validation_log`.
  - **Request body** (`QuestionGenerationRequest`):
    ```json
    {
      "concept_id": "uuid",
      "concept_name": "string",
      "learning_goal": "string",
      "bloom_level": "Remembering" | "Understanding" | "Applying" | "Analyzing" | "Evaluating" | "Creating",
      "difficulty_tier": "easy" | "medium" | "hard"
    }
    ```
  - **Response body** (`QuestionBatchResponse`):
    ```json
    {
      "concept_id": "uuid",
      "bloom_level": "string",
      "difficulty_tier": "string",
      "questions": [
        {
          "id": "uuid",
          "question_type": "MCQ" | "MCQMultiSelect" | "TrueFalse" | "FillInBlank",
          "question_text": "string",
          "options": ["string"] | null,
          "correct_answers": ["string"],
          "explanation": "string",
          "estimated_time_seconds": 30,
          "tags": ["string"],
          "validation_status": "Passed" | "Warning"
        }
      ]
    }
    ```
  - There is no separate `/v1/questions/validate` endpoint — validation isn't a
    standalone callable step, it's an inseparable part of `generate`.
  - No IRT metadata (`difficulty_b`/`discrimination_a`/`guessing_c`) — that was
    replaced by the simpler `difficulty_tier` label (see
    `docs/product/adaptive-engine-review.md`, point 3).

- **GET `/v1/questions/{question_id}`** — **NOT STARTED, next step**
  - **Purpose**: Return a stored question by ID so `quiz-session-service` (still
    an empty stub) can fetch what to serve. Nothing outside this service can
    read `questions` yet.

---

### 2.4 Feedback & Quality Loop (MVP Required)

- **POST `/v1/questions/{question_id}/feedback`**
  - **Purpose**: Capture user feedback to feed `question_feedback_log`.
  - **Request body**:
    ```json
    {
      "response_id": "uuid (optional)",
      "rating": 1,
      "flag_reason": "Confusing / Incorrect / ... (optional)",
      "notes": "string (optional)"
    }
    ```
  - **Response body**:
    ```json
    { "ok": true }
    ```

---

### 2.5 Moderator / Admin Endpoints

- **GET `/v1/moderation/flags`** (role: moderator/admin)
  - **Purpose**: List questions that have been flagged by users.
  - **Query params**:
    - `status` (optional)
    - `reason` (optional)
    - `limit` (optional)
    - `cursor` (optional, for pagination)

- **GET `/v1/moderation/validation-failures`** (role: moderator/admin)
  - **Purpose**: List questions that failed validation according to `question_validation_log`.

- **POST `/v1/moderation/questions/{question_id}/status`** (role: moderator/admin)
  - **Purpose**: Approve / reject / disable a question for serving.
  - **Request body**:
    ```json
    {
      "status": "approved" | "rejected" | "disabled",
      "reason": "string (optional)"
    }
    ```

---

## 3. Suggested FastAPI Router Structure

- `question_generation_service/main.py`
  - Create `FastAPI` app.
  - Include routers:
    - `api.thema_router`
    - `api.question_router`
    - `api.moderation_router`

- `question_generation_service/api/thema_router.py`
  - Endpoints: `/health`, `/v1/thema/extract`, `/v1/concepts/map`

- `question_generation_service/api/question_router.py`
  - Endpoints: `/v1/questions/generate`, `/v1/questions/validate`, `/v1/questions/{question_id}`, `/v1/questions/{question_id}/feedback`

- `question_generation_service/api/moderation_router.py`
  - Endpoints: `/v1/moderation/flags`, `/v1/moderation/validation-failures`, `/v1/moderation/questions/{question_id}/status`

---

## 4. Implementation Order (Recommended)

1. **Basic service + health** — DONE
2. **Thema, concept, exposure & BKT init** — DONE
   - `/v1/thema/extract` (+ `refine`, `confirm`), `/v1/thema/{id}/exposure`,
     `/v1/concepts/map`. `confirm()` maps concepts (reusing existing ones per
     thema/topic) and checks exposure in one call; BKT init runs immediately
     if exposure is already known, otherwise after the exposure endpoint.
3. **Question generation + validation + judge** — DONE
   - `/v1/questions/generate`: Prompt 3, deterministic Step 8A checks, and an
     independent Prompt 4 judge (re-derives its own answer/checks alignment,
     never shown the draft's stated answer) before storing.
   - Covered by 126 unit tests + integration tests against a real Postgres
     instance + a gated live-AI test (`RUN_LIVE_MISTRAL_TESTS=1`) that hits
     the real Mistral API and prints generated content for manual review.
4. **`GET /v1/questions/{question_id}`** — **NOT STARTED, next step**
   - Nothing outside this service can read a stored question yet;
     `quiz-session-service` needs this to serve anything at all.
5. **Feedback endpoint** — NOT STARTED
   - `/v1/questions/{question_id}/feedback` inserting into `question_feedback_log`.
6. **Moderation endpoints** — NOT STARTED
   - `moderation_router.py` exists but is an empty stub — no endpoints yet.

### Beyond this service's scope

The bigger gap is outside `question-generation-service` entirely:
`quiz-session-service` and `learning-engine-service` are both empty stubs
(health check only). Nothing today can select a question for a specific
learner, track a `quiz_sessions` row, record a `user_responses` row, or run
`update_bkt()` after an answer (main-workflow.md Steps 9–11). Question
generation (Step 8) has nowhere to serve into yet.
