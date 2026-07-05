# Question Generation Service – Implementation Plan

This document describes what needs to be developed for the `question-generation-service` (FastAPI + Mistral) and how it should be structured.

---

## 1. Service Responsibilities (High-Level)

The service is responsible for:

1. **Thema & Concept Analysis**
   - Turn raw user text into a normalized `thema` + `topics`.
   - Generate thema and their possible topics

2. **Question Generation & Validation**
   - Generate questions from concept–Bloom pairs using Mistral.
   - Attach IRT-like metadata (difficulty, discrimination, guessing).
   - Validate questions and log validation results.

3. **Question Retrieval & Feedback**
   - Provide read access to stored questions.
   - Accept user feedback (ratings, flags) for quality improvement.

4. **Moderation & Quality Monitoring**
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

### 2.2 Thema & Concept Analysis

- **POST `/v1/thema/extract`** (Prompt 1)
  - **Purpose**: Convert raw user input into a canonical `{ thema, topic }`.
  - **Request body**:
    ```json
    {
      "text": "string",
      "language": "string (optional)"
    }
    ```
  - **Response body**:
    ```json
    {
      "thema": "string",
      "topic": "string",
      "normalized_input": "string"
    }
    ```

- **POST `/v1/concepts/map`** (Prompt 2)
  - **Purpose**: Produce atomic concepts, Bloom levels, and quiz-planning metadata
    (`learning_goal`, `estimated_time_minutes`, `complexity_level`) for a thema's topics,
    and persist them to `learning_units`.
  - **Trigger**: called **internally by `ThemaService.confirm()`**, not by the client —
    once a learner confirms their thema+topics, the backend maps concepts for all
    topics in one call before marking the extraction confirmed. If concept mapping
    fails, the extraction is left in its pre-confirm state so the client can retry
    `confirm()` rather than ending up "confirmed" with no concepts. The HTTP endpoint
    still exists for standalone/admin use (e.g. re-mapping, moderation tooling).
  - **Request body**:
    ```json
    {
      "thema": "string",
      "topics": ["string"],
      "learner_context": { "profession": "string", "education_level": "string" } // optional
    }
    ```
  - **Response body**:
    ```json
    {
      "thema": "string",
      "concepts": [
        {
          "id": "uuid",
          "topic": "string",
          "concept": "string",
          "learning_goal": "string",
          "bloom_levels": ["Remembering", "Understanding", "..."],
          "estimated_time_minutes": 15,
          "complexity_level": "Low" | "Medium" | "High"
        }
      ]
    }
    ```

---

### 2.3 Question Generation & Validation

- **POST `/v1/questions/generate`** (Prompt 3 + store + validation)
  - **Purpose**:
    - Generate `N` questions for given concept–Bloom pairs using Mistral.
    - Attach IRT-style metadata.
    - Validate each question.
    - Store valid questions in the database and return them.
  - **Minimal request body**:
    ```json
    {
      "thema": "string",
      "topic": "string",
      "concept_bloom": [{ "concept": "string", "bloom_level": "string" }],
      "question_types": ["mcq", "true_false", "fill_blank"],
      "count": 10,
      "language": "string (optional)",
      "user_context": { "profile": "..." } // optional
    }
    ```
  - **Response body**:
    ```json
    {
      "questions": [
        /* QuestionDTO[] */
      ],
      "validation": {
        "passed": 0,
        "failed": 0
      }
    }
    ```

- **POST `/v1/questions/validate`**
  - **Purpose**: Validate a question payload (same logic as `validate_question()` in docs) and log to `question_validation_log`.
  - **Request body**:
    ```json
    {
      "question": {
        /* QuestionDTO */
      }
    }
    ```
  - **Response body**:
    ```json
    {
      "status": "passed" | "failed" | "warning",
      "score": 0.0,
      "failed_checks": ["string"]
    }
    ```

- **GET `/v1/questions/{question_id}`**
  - **Purpose**: Return a stored question so other services (e.g. `quiz-session-service`) can fetch it by ID.
  - **Response body**:
    ```json
    {
      /* QuestionDTO */
    }
    ```

> **QuestionDTO (conceptual)**  
> Fields should align with the `questions` table (stem, options, correct answer, explanation, concept_id, bloom_level, difficulty_b, discrimination_a, guessing_c, language, etc.).

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

1. **Basic service + health**
   - Implement `FastAPI` app + `/health`.
2. **Thema & concept endpoints** — DONE
   - `/v1/thema/extract` (+ `refine`, `confirm`) and `/v1/concepts/map`.
   - `ThemaService.confirm()` calls concept mapping internally once a learner
     confirms their thema/topics — see §2.2 for the trigger/failure semantics.
3. **Question generation (stubbed)**
   - `/v1/questions/generate` returning mocked questions with correct schema.
4. **Validation logic + logging**
   - `/v1/questions/validate` and logging to DB (or stub).
5. **Feedback endpoint**
   - `/v1/questions/{question_id}/feedback` inserting into `question_feedback_log`.
6. **Moderation endpoints**
   - Implement listing and status update endpoints using the DB.

This gives you a clear roadmap from HTTP contract → internal structure → implementation order.
