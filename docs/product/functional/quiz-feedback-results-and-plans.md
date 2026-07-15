# Quiz Feedback Modes, Session Results, Plans & Manual Quizzes

**Status legend:** ✅ done · 🟡 in progress · ⬜ not started
**Agreed:** 2026-07-13 · **Owner doc for:** feedback timing, end-of-session results, session history, AI entitlement, manual quiz builder.

---

## 1. Product decisions (locked)

### 1.1 Feedback timing — per-session choice

Chosen by the learner on the quiz page before starting a session:

| Mode                  | During the session                                                                      | On the results page                                                                    |
| --------------------- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| `immediate`           | Correct/wrong + expected answer + explanation after each answer (current behavior)      | Full review                                                                            |
| `end` (**default**)   | Answer recorded silently — no correctness shown, progress header shows no correct count | Full review                                                                            |
| `never` ("Exam mode") | Same as `end`                                                                           | Score + per-question correct/wrong only; expected answers and explanations stay hidden |

The last chosen mode is **remembered per user** and pre-selected next time.

### 1.2 End-of-session results page (always shown, all modes)

- Score % with a color gauge, 6 bands:
  `0–29 red · 30–44 orange · 45–59 amber · 60–74 yellow · 75–89 light green · 90–100 green`
- Stats: correct/total, accuracy %, total time.
- List of every question in answered order, each marked correct (green) / wrong (red).
- Expanding a question shows: **the user's answer** (colored by correctness), **the expected answer**, and **the explanation stored with the question** — except in `never` mode (correctness only).

### 1.3 Session history

Learners can list their past sessions (date, score %, correct/total, duration) globally and per quiz, and open any past session's results page (same review view, same `never`-mode redaction).

- **Global History page** (`/app/history`, nav item "History"): all sessions newest first, with two views — **By date** (grouped Today / Yesterday / date) and **By quiz** (grouped per quiz with attempt count and best score). Naming rule: "History" = the cross-quiz list; "Results" = a single session's review page.
- **History survives quiz deletion.** Deleting a quiz is a **soft delete** (`quizzes.deleted_at`): the quiz disappears from listings/detail/start, but its sessions keep their title, topics, and full per-question review. Such rows carry a quiet "Quiz deleted" badge; retake is unavailable (results page hides "Retake quiz", by-quiz group header isn't a link). A session already in flight when its quiz is deleted can still be finished.
- Sessions whose quiz row is entirely gone (future hard purge) fall back to the session's stored `thema` as label.

### 1.4 No LLM calls at answer time — ever (cost + latency)

Already true today and must stay true:

- `explanation` and `correct_answers` are generated **once, with the question** (generation prompt requires them).
- The judge **blind-derives** the correct answers itself (it is never shown the generator's claimed answer), so stored answers are LLM-verified before any learner sees them.
- Grading (`answers_match`) is pure string comparison in the service.
- **Gap to close (Phase 5):** the judge does not currently validate the _explanation text_ — add an explanation-consistency check to the judge pass.

### 1.5 Quiz types: AI vs manual

- `quizzes.source`: `ai` (existing flow) | `manual` (new builder, currently a "Coming soon" stub).
- Manual quizzes: creator authors questions, options, correct answer(s), and optional explanation — that authored content **is** the feedback. No LLM involvement at any point.
- Manual sessions skip BKT/IRT adaptive selection (no concept graph) — sequential or shuffled order.

### 1.6 Plans / AI entitlement

- MVP: `users.ai_enabled` boolean, toggled manually until billing exists; billing later just flips it.
- Gates **creation-time AI only**: AI quiz creation, wizard, generation. Returns 403 when disabled.
- Never gates playback/review: a lapsed subscriber keeps full access to previously generated quizzes, sessions, and feedback (all pre-generated — no LLM needed).
- Frontend hides/disables AI creation paths for unentitled users and shows an upgrade prompt.

### 1.7 Grading rules

- Multi-answer questions: **all-or-nothing** (no partial credit).
- Free-text answers (incl. manual quizzes): graded **without LLM** — normalize (lowercase, trim, collapse whitespace, strip punctuation/accents) → match against the accepted-answers list → typo tolerance (Levenshtein ≤ 1 short answers, ≤ 2 longer). Possible later addition (non-exam modes): "I was actually right" self-override.

---

## 2. Implementation plan & status

### Phase 1 — Feedback modes + results page ✅ (2026-07-13 — code complete, lint/type clean, migration applied, **verified end-to-end in the running app** — all 3 modes driven via Playwright, redaction confirmed at the API)

| Step | Item                                                                                                                                                                                                  | Status |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| 1.1  | Migration: `quiz_sessions.feedback_mode` (`immediate\|end\|never`, default `end`) + `users.default_feedback_mode` (`20260713180000_session_feedback_mode.js`)                                         | ✅     |
| 1.2  | Backend: `POST /v1/quizzes/{id}/sessions` accepts `feedback_mode` (falls back to user default), persists it, updates user default; `GET /v1/me/session-preferences` returns the remembered default    | ✅     |
| 1.3  | Backend: `submit_answer` redacts `is_correct`/`correct_answers`/`explanation` from `AnswerResult` when mode ≠ `immediate`; `SessionState.correct_count` hidden mid-session outside `immediate`        | ✅     |
| 1.4  | Backend: `GET /v1/sessions/{id}/review` — summary + per-question entries (question text, options, user answer, is_correct, expected answers, explanation), redacted per mode, completed sessions only | ✅     |
| 1.5  | Frontend: feedback-mode selector on quiz detail page (pre-selected from user default)                                                                                                                 | ✅     |
| 1.6  | Frontend: session page — mode-aware (silent advance, no feedback panel outside `immediate`)                                                                                                           | ✅     |
| 1.7  | Frontend: results page — SVG score gauge (6 color bands), stats, per-question expandable review (`shared/components/quiz/session-results.tsx`)                                                        | ✅     |

### Phase 2 — Session history ✅ (2026-07-13 — verified end-to-end)

- `GET /v1/sessions` (current user, optional `quiz_id` filter, `limit` ≤ 200) → per-session stats, newest first. ✅
- Frontend: "Previous sessions" card on the quiz detail page (`shared/components/quiz/session-history.tsx`) — colored score %, date, mode, "View results" → session results page; in-progress sessions show "Resume". ✅
- Global history page (across quizzes): ✅ (2026-07-14) — `/app/history` + "History" nav item; `GET /v1/sessions` entries now carry `quiz_title`/`quiz_deleted`/`thema` (batch ref lookup, includes tombstones); `SessionSummary` carries the same so the results page can label and badge.

### Phase 2b — Quiz soft delete ✅ (2026-07-14)

Quiz delete destroyed session history (`quiz_sessions.quiz_id` was `ON DELETE CASCADE` — code-review 2026-07-14 finding 1). Now:

- Migration `20260714100000_quizzes_soft_delete.js`: `quizzes.deleted_at`; FK → `ON DELETE SET NULL` (backstop for a future hard purge); `idx_quizzes_owner_recent` made partial (`WHERE deleted_at IS NULL`); `quiz_sessions(user_id, start_time DESC)` index for history (replaces single-column `user_id` index).
- Backend: `QuizRepository.delete` = tombstone update (quiz_concepts kept for topic labels); listings filter tombstones; `QuizService`/session-start 404 them; in-flight sessions and review still resolve them.
- A retention job may later hard-purge old tombstones (sessions survive via `SET NULL`); GDPR account deletion still hard-cascades everything via `users`.

### UI fix — quizzes page view switcher ✅ (2026-07-13)

`--secondary` and `--muted` are identical in the theme, so the active `SegmentedControl` segment was invisible. Reworked: active segment = raised `bg-background` pill + shadow on the muted track; Ready/Generating filters = round chips, filled primary when active.

### Phase 3 — Plans / AI entitlement ⬜

- Migration: `users.ai_enabled` (boolean, default false — decide default with rollout).
- Backend: entitlement dependency guarding AI endpoints (quiz creation w/ generation, wizard) → 403.
- Frontend: hide AI creation for unentitled users, upgrade prompt.

### Phase 4 — Manual quiz builder ⬜ (biggest)

- Migration: `quizzes.source` (`ai|manual`) + direct quiz→question link (join table or nullable `questions.quiz_id`; today questions are pooled per concept for adaptive selection).
- Backend: manual quiz CRUD (questions: MC single/multi, true/false, free text w/ accepted-answers list, optional explanation); sequential session flow bypassing BKT.
- Frontend: replace `ComingSoon` at `app/quiz/new/manual` with the builder. Session + results pages reused unchanged.

### Phase 5 — Judge explanation-consistency check ⬜

- Extend judge output to flag explanations contradicting its blind-derived answers; regenerate flagged questions' explanations.

---

## 3. Key code touchpoints

| Area                       | Files                                                                                                                                                           |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Session flow (backend)     | `packages/question-generation-service/.../services/session_service.py`, `routers/session_router.py`, `schemas/session.py`, `repositories/session_repository.py` |
| Grading                    | `services/question_validation_service.py` (`answers_match`)                                                                                                     |
| Generation/judge prompts   | `prompts/question_generation.py`, `prompts/question_judge.py`                                                                                                   |
| Migrations                 | `packages/migration-service/migrations/` (new files only)                                                                                                       |
| Session UI                 | `apps/web-app/src/app/app/sessions/[id]/page.tsx`                                                                                                               |
| Quiz detail (start button) | `apps/web-app/src/app/app/quizzes/[id]/page.tsx`                                                                                                                |
| Frontend actions/types     | `apps/web-app/src/shared/lib/actions/session-actions.ts`, `shared/types/session.ts`                                                                             |
| Manual builder stub        | `apps/web-app/src/app/app/quiz/new/manual/page.tsx`                                                                                                             |

Update the status tables above as phases land.
