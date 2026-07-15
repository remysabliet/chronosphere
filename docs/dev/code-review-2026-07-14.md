# Code Review — 2026-07-14 (uncommitted working tree on `develop`)

Scope: uncommitted changes + new untracked files (~51 files, ~1,144 insertions) —
quiz list/detail pages, session-taking with feedback modes, quiz deletion,
session history/results, generation-jobs completion tracking, and the two new
migrations. 10 findings survived verification (9 CONFIRMED, 1 PLAUSIBLE), plus
4 lower-priority notes.

Legend: ⬜ not started · ✅ fixed · 🔶 decision pending · ❌ won't fix

**Status (2026-07-15):** findings **1–6, 9 ✅ fixed**, findings
**7, 8, 10 ⬜ still open** (7: `refetchInterval` still on the quizzes
`useInfiniteQuery`; 8: review-error dead end unchanged; 10: pyright still
errors on `test_thema_prompt.py:34` when checked directly). Notes: N3
resolved (tests authorized), N4 pends on 7; N1/N2 open.

**Status (2026-07-15):** finding **8 ✅ fixed**; **6, 7, 9, 10 ⬜ still open**.

**Status (2026-07-15, later):** findings **6, 9, 10 ✅ fixed** — only
**7 ⬜ still open** (list-level `refetchInterval` poll; N4 pends on it).

**Status (2026-07-15, final):** finding **7 ✅ fixed** (SSE push replaced all
progress polling — see item 7), which also closes **N4**. All findings
resolved.

---

## 1. ✅ Quiz delete destroys session history (CASCADE) — fixed: soft delete + History page

**Severity: highest.** `QuizRepository.delete`'s comment claims sessions are
kept ("a learner's history outlives the quiz config"), but migration
`20260708100100_quiz_sessions_quiz_id.js` declares `quiz_sessions.quiz_id`
with `ON DELETE CASCADE`. Deleting a quiz erases every session recorded
against it (and orphans `user_responses` via `SET NULL`) — exactly the history
the new session-history/results pages display. BKT mastery (`concept_progress`)
is unaffected.

**Agreed direction (2026-07-14):** history must outlive the quiz, viewable
even after deletion.

- New migration: FK `quiz_sessions.quiz_id` → `ON DELETE SET NULL`.
- Fix the misleading comment in `quiz_repository.delete`.
- New `/app/history` page: all of the user's sessions, newest first — backend
  `history` endpoint already supports the no-quiz-filter form and sessions
  store `thema` denormalized, so entries for deleted quizzes keep a label.
  Each row links to the existing session results page (`/app/sessions/{id}`),
  which works without the quiz row (results = session + responses + questions;
  questions belong to concepts, not quizzes).
- Nav entry for History; delete-quiz dialog copy: past results remain in History.

**Implemented (2026-07-14)** — went one step further than SET NULL: quiz
deletion is now a **soft delete** (`quizzes.deleted_at`, migration
`20260714100000_quizzes_soft_delete.js`), so history keeps the quiz's real
title and full review, not just the thema fallback. FK is `ON DELETE SET
NULL` as a backstop for a future hard purge. Listings/detail/session-start
404 tombstones; `/app/history` (by-date and by-quiz views) ships with
"Quiz deleted" badges; `GET /v1/sessions` + summary now carry
`quiz_title`/`quiz_deleted`/`thema`. Index changes:
`idx_quizzes_owner_recent` partial on live rows,
`quiz_sessions(user_id, start_time DESC)` for history. Details:
`docs/product/functional/quiz-feedback-results-and-plans.md` §1.3/Phase 2b,
`docs/architecture/db-schema.md`.

**Verified end-to-end (2026-07-14, running app + dev bypass):** seeded quiz →
full session via API → delete → detail/start 404, list filtered, history
entry keeps title + `quiz_deleted: true`, review returns all entries with
explanations; DB shows tombstone set and session row intact
(`quiz_id` kept, `completed`); GUI (Playwright) confirmed History by-date and
by-quiz views with the "Quiz deleted" badge, unlinked group header, and
results page with badge and no Retake button.

## 2. ✅ Migration backfill can mark in-flight quizzes ready

`20260713150000_quizzes_generation_jobs.js` backfills
`generation_jobs_completed = generation_jobs_total` for every quiz. That was
verified against one local DB; on any DB with jobs still in flight the quiz
flips to "ready" with a partial pool, and later `record_job_completion`
increments push `jobs_completed > jobs_total` (no clamp).

**Proposed:** clamp the worker increment —
`generation_jobs_completed = LEAST(generation_jobs_completed + 1, generation_jobs_total)`
in `QuizRepository.record_job_completion` — and reword the migration comment to
state its assumption. (The DB can't know whether a Redis job is in flight, so
the backfill itself can't be made perfect; the clamp makes damage self-limiting.)

## 3. ✅ Session-service test suites broken by new signatures

`SessionService.__init__` gained a required `user_repository` arg and
`start()` a required `feedback_mode` arg, but `tests/unit/test_session_service.py`
(`make_service` + ~11 `service.start(quiz.id, owner)` calls, incl. the new
identity-map-expiry regression test — which has therefore never passed) and
`tests/integration/test_session_flow_integration.py` were not updated.
`FakeSession` also lacks the `feedback_mode` attribute `_state()` reads, and
the integration test asserts `result.is_correct is False` which is now `None`
under the default `end` mode.

**Proposed:** add a `FakeUserRepository` (get/set default feedback mode), pass
it in `make_service` + integration setup, add `feedback_mode` to
`FakeSession`/`create()`, pass the third `start()` arg everywhere
(`'immediate'` in tests asserting grading is returned).

**Verified implemented (2026-07-14):** all proposed pieces present in both
files; unit suite passes 9/9. Integration suite not executed (needs the test
DB) but its setup matches the new signatures (`UserRepository` passed,
`start(..., 'immediate')` so the `is_correct is False` assertion is valid).

## 4. ✅ Feedback preference silently clobbered

Two halves:

- **Frontend** (`quizzes/[id]/page.tsx:123`): `selectedMode` falls back to
  `'end'` while `GET /v1/me/session-preferences` is still loading, Start is not
  disabled during that window, and the resolved mode is always sent — the
  backend then persists it as the new default. Slow network + stored
  `'immediate'` → session runs in `'end'` mode AND stored default overwritten.
  **Proposed:** send `feedback_mode` only when the user actually clicked the
  selector this visit (else omit → backend uses the stored default).
- **Backend** (`session_service.py:138`): `start()` commits the preference
  _before_ validating the quiz exists / is visible / has questions, so a failed
  start still mutates the stored default. **Proposed:** validate first, hoist
  needed quiz attributes into locals (the commit-expires-identity-map
  constraint documented in the code), then persist the preference.

**Implemented (2026-07-14):** backend half — `start()` validates, hoists,
selects the first question, and only then persists; `feedback_mode=None`
means "use stored default, persist nothing". Frontend half —
`startSessionAction` now takes `FeedbackMode | null` and the detail page
sends the raw clicked state (`null` when the selector wasn't touched this
visit), so the stored default is only ever written on an explicit click;
`selectedMode` remains UI-highlight-only. The Start gate changed from
`!preferencesQuery.isSuccess` to `preferencesQuery.isPending`: still no
start while the highlight is unknown, but a failed preferences fetch no
longer dead-ends the button (backend falls back to the stored default).

## 5. ✅ Delete button visible to non-owners; shared-quiz delete policy resolved

- **Bug (agreed to fix):** the UI infers ownership from
  `quiz.owner_name === null`, but `users.name` is nullable and
  `quiz_service.get` returns `owner_name=None` for owners _and_ for nameless
  owners — so non-owners can see Delete on a shared quiz (backend still blocks
  with 404, a confusing toast). **Fix:** add explicit `is_owner: bool` to
  `QuizDetailResponse`/`QuizListItem` (service already computes it), mirror in
  the TS types, gate the Delete UI on it.
- **Decision (2026-07-14): owners can always delete, shared or not, via the
  existing soft delete (`quizzes.deleted_at`).** Rationale: a quiz is config
  only (questions live in the pools; sessions carry their own `question_ids`
  and stats), so deletion destroys nobody's content. Making shared quizzes
  undeletable is what would create the zombie/duplicate-title clutter.
  - Deletion hides the quiz from **all** lists (owner and others) and blocks
    new sessions.
  - Existing session history stays intact and viewable (title read from the
    soft-deleted row; results = session + responses + questions). Show a small
    "quiz removed" note on those history entries.
  - In-flight sessions of other users finish normally — the next-question
    lookup for an already-active session must not filter on
    `deleted_at IS NULL`.
  - **No purge job for now.** Purging is only safe for quizzes no session (by
    anyone) references — otherwise history loses titles; rows are tiny, revisit
    later if ever needed.
- **"Save to my quizzes" (keep a shared quiz for yourself):** fork-on-save, not
  reference counting/co-ownership (keeps single-owner model).
  - Backend: `POST /quizzes/{id}/copy` → `QuizService.copy()` clones the
    `Quiz` row (new id, `owner_user_id` = requester, `visibility` reset to
    `private`) + its `quiz_concepts` rows; copy is immediately ready
    (`generation_jobs_completed = generation_jobs_total`) since questions
    already exist in the pool. Auth: refuse copying another user's private
    quiz (same rule as viewing); **allow** copying a soft-deleted quiz only if
    the requester has a session referencing it (prevents enumerating deleted
    quizzes by id) — this is the retroactive resurrect-after-deletion path.
  - UI: same `is_owner` gate as Delete — owners see Delete, non-owners see
    "Save to my quizzes" in the same slots: quiz-card top-right icon
    (`quiz-card.tsx`) and quiz-detail header action group
    (`quizzes/[id]/page.tsx`). Later: "Save a copy" on history entries whose
    quiz was deleted.
- **Duplicate titles among live quizzes** (independent of deletion): rely on
  list metadata already shown (owner, created date, question count, topics);
  optionally de-collide per owner at creation with a "(2)" suffix scoped to
  non-deleted quizzes. No global title uniqueness — titles are labels, ids are
  keys.

**Implemented (2026-07-14):** `is_owner: bool` on
`QuizListItem`/`QuizDetailResponse` (+ TS mirrors) now gates Delete, the
rename pencil, and "Save to my quizzes". `POST /v1/quizzes/{id}/copy` →
`QuizService.copy()` → `QuizRepository.create_copy()` (clones the config row
with `visibility='private'`, jobs counters pinned to the source's completed
count so the copy is immediately ready, and insert-selects `quiz_concepts`);
soft-deleted sources copyable by owner or by users with a referencing session
(`SessionRepository.user_has_session_for_quiz`), 404 otherwise. Frontend:
`copyQuizAction` + `useCopyQuiz` hook; card corner shows Delete (owner) or
BookmarkPlus save (non-owner); detail header shows Delete or a
"Save to my quizzes" button that navigates to the new copy. In-flight
sessions on deleted quizzes were already safe (session_service resolves
tombstones via `_quiz_by_id`). Deferred: "Save a copy" action on
deleted-quiz history entries; per-owner "(2)" title de-collision.

## 6. ✅ History vs summary disagree on accuracy

`history()` computes `correct / total_questions` (answered) while
`_summary_of()` computes `correct / len(question_ids)` (served); for an
in-progress session (one served-but-unanswered question always present) the
two report different percentages for the same session.

**Proposed:** build each `SessionHistoryEntry` from `_summary_of(session)` so
one formula owns accuracy/status.

**Implemented (2026-07-15):** `_summary_of()` is the single owner and now uses
the **answered** denominator (`session.total_questions`), not served — the
pending unanswered question no longer drags accuracy down mid-session.
`history()` builds each entry from it; `SessionHistoryEntry` now extends
`SessionSummary` (adds `feedback_mode`/`started_at`). Completed sessions are
unchanged (both counts converge at completion).

## 7. ✅ Quiz list poll refetches every loaded page

`quizzes/page.tsx:72` puts `refetchInterval: 3000` on a `useInfiniteQuery`;
React Query refetches an infinite query by re-running **all** loaded pages, so
a user N pages deep with one generating quiz fires N list requests every 3 s.

**Proposed:** drop the list-level poll; a generating quiz's card uses the
existing per-quiz `useQuizProgress` hook (polls that quiz's detail) and
invalidates the list once when status flips to ready. Also centralizes the
"poll while generating" rule that is currently duplicated (see note N4).

**Implemented (2026-07-15) — went past the proposal: polling replaced with SSE
push** (per user decision; supersedes the "polling now, SSE later" call in
ui-update-plan §3). The generation worker publishes each job completion to
Redis pub/sub (`events:quiz-progress:{user_id}`; `RedisPubSub` seam in
`memosphere_messaging`, counters from `record_job_completion(...RETURNING)`,
payload built by `quiz_service.build_progress_event()` so push and REST share
the status/clamp rules). `GET /v1/quizzes/events` streams it as SSE (JWT-only
auth — no DB-backed dep pinning a pooled connection for the stream's life);
the browser's `EventSource` connects via the Next proxy `/api/quiz-events`,
which attaches the bearer token. `useQuizEvents()` patches `['quiz', id]` and
`['quizzes']` caches in place and invalidates the list **once** on the
`generating → ready` flip; reconnects refetch to cover missed events. Both
`refetchInterval`s and `TIMEOUTS.QUIZ_PROGRESS_POLL` are gone, which also
resolves the duplicated poll rule (note N4).

## 8. ✅ Results-page error state is a dead end

`sessions/[id]/page.tsx:128`: if the completed-session review fetch fails
once, the page shows only "These results couldn't be loaded." — no retry, no
navigation, and the score the client already knows (immediate mode) is hidden.
The component this diff replaced always showed score + "Back to quizzes".

**Proposed:** on error, render the client-known score when available, a Retry
button (refetch), and a "Back to quizzes" link.

**Implemented (2026-07-15):** the review-error branch now renders a
`ResultsError` card: client-known score from `state.correct_count` /
`state.total_questions` when non-null (immediate mode), a Retry button wired
to `reviewQuery.refetch()` (disabled with "Retrying…" while
`reviewQuery.isFetching`), and a "Back to quizzes" link (`ROUTES.QUIZZES`).
The "Preparing your results…" loading text is unchanged.

## 9. ✅ Ungraded responses rendered as wrong (PLAUSIBLE)

`session_service.review()` line 324 does `bool(response.is_correct)`;
`user_responses.is_correct` is nullable (legacy rows), so an ungraded response
renders as answered-wrong and drags the score down.

**Proposed:** make `is_correct` `bool | None` through `SessionReviewEntry` and
the TS type; frontend renders null as a neutral "not graded" state, excluded
from the score.

**Implemented (2026-07-15):** `is_correct` is now `bool | None` in
`SessionReviewEntry` (Python + TS) and `review()` passes the raw value through.
`session-results.tsx` renders null as a neutral row (muted border, minus icon,
"Not graded" label) instead of red/wrong. The gauge score was never affected —
`summary.correct_answers` is counted server-side and ungraded rows were never
in it; only the per-entry rendering was wrong.

## 10. ✅ Pyright index error in new test file

`tests/unit/test_thema_prompt.py:34` subscripts
`_INTERPRETATION_SCHEMA["properties"]["topics"]` where the schema is typed
`dict[str, object]` → `reportIndexIssue`. (Currently masked because
`pyrightconfig.json` only includes `src`.)

**Proposed:** type the schema as a proper `TypedDict` in
`prompts/thema_topic_extract.py` (or cast at the subscript sites).

**Implemented (2026-07-15):** `_ObjectSchema` `TypedDict` (`type`,
`properties`, `required`, `additionalProperties`) in
`prompts/thema_topic_extract.py`; `_INTERPRETATION_SCHEMA` is annotated with
it, so the test's `["properties"]["topics"]` subscripts are typed. Pyright
clean on both files when checked directly; test file unchanged.

---

## Lower-priority notes (cut by the 10-finding cap)

- **N1 — ready/generating predicate duplicated:** Python
  (`quiz_service._status`) and SQL (`quiz_repository.list` filter) both encode
  `jobs_completed >= jobs_total`, tied only by a comment — the same pattern
  whose previous incarnation (`_expected_count_expr`) drifted and caused the
  stuck-in-generating bug this diff fixes. Deeper fix: one SQLAlchemy
  `hybrid_property` on `Quiz` (would ripple into `QuizEntryProtocol` + test
  fakes).
- **N2 — dev-bypass identity duplicated:** sub
  `00000000-0000-4000-8000-000000000001` / `dev-bypass@local.test` hardcoded in
  both `dependencies/auth.py` and `apps/web-app/src/shared/lib/auth.ts`; only
  the boolean flag is shared via env. Fix: shared `DEV_BYPASS_SUB`/`DEV_BYPASS_EMAIL`
  env pair in docker-compose.
- **N3 — testing policy:** `.claude/CLAUDE.md` says "Do NOT write or run tests
  until told the project has reached its end phase"; the diff adds new tests
  (`test_thema_prompt.py` + 3 new test functions elsewhere). Flagged in case
  unintentional; user has since asked for tests to be fixed, so treated as
  authorized.
- **N4 — poll-while-generating rule duplicated** between `quizzes/page.tsx`
  and `use-quiz-progress.ts` — resolved by the fix proposed in point 7.
  ✅ Closed 2026-07-15: both polls removed outright (SSE push, see point 7).

## Decisions log

- 2026-07-14 — Point 1: history outlives quiz deletion; History page +
  FK → `SET NULL` (user + Claude agreed).
- 2026-07-14 — Point 5 policy resolved (user + Claude agreed): owners always
  delete via existing soft delete; hidden everywhere, no new sessions, history
  intact, in-flight sessions finish; no purge job. Non-owners keep a shared
  quiz via fork-on-save ("Save to my quizzes", `POST /quizzes/{id}/copy`),
  including retroactively on soft-deleted quizzes they have sessions for.
  Supersedes the earlier "open" entry; `is_owner` gate unchanged.
- 2026-07-14 — Cascade-delete of history initially accepted as expected
  behavior, superseded by the History-page decision above.
