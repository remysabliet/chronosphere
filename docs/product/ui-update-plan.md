# 🎨 UI Update Plan — Library-Centric Navigation

Status: **approved, not yet implemented** (2026-07-08)

## Problem

The app is creation-centric with nowhere to _see_ anything:

- Only end-to-end working feature is the quiz-creation wizard. Dashboard, Memocards, Analytics, Profile, Manual creation are all `ComingSoon` stubs.
- No page lists quizzes; no page to take one; backend has **zero GET endpoints** (only `POST /v1/quizzes`).
- Creation dead-ends: wizard success bubble links "Back to dashboard" (a stub) and discards the returned quiz `id`.
- `quizzes.visibility` (`private | shared | public`) exists in DB + `types/quiz.ts` but is never sent, read, or enforced. Shared quizzes are NOT in the product docs (Phase-3 "shared decks" only) — adding them is a deliberate scope addition; the data model already supports it.

## Decisions

### 1. Sidebar (`shared/components/layout/app-nav.tsx`)

Enabled items first; unimplemented items greyed with a "Soon" pill, in roadmap order:

| #   | Label     | Icon (lucide)     | Route            | State                            |
| --- | --------- | ----------------- | ---------------- | -------------------------------- |
| 1   | Quizzes   | `Library`         | `/app/quizzes`   | enabled — **post-login landing** |
| 2   | New Quiz  | `PlusCircle`      | `/app/quiz/new`  | enabled                          |
| 3   | Home      | `LayoutDashboard` | `/app/home`      | greyed "Soon"                    |
| 4   | Memocards | `Layers`          | `/app/memocards` | greyed "Soon"                    |
| 5   | Analytics | `BarChart3`       | `/app/analytics` | greyed "Soon"                    |
| 6   | Profile   | `User`            | `/app/profile`   | greyed "Soon"                    |

- "Dashboard" is renamed to **Home** and greyed (not deleted): it becomes the FSRS "Memory Refresh" hub later (see §6) and then takes over as landing.
- `NAV_ITEMS` gains `enabled: boolean`. Disabled items render as `<span aria-disabled='true'>` (NOT a `Link`), `opacity-50 cursor-not-allowed text-muted-foreground`, right-aligned "Soon" pill (`ml-auto rounded-full bg-muted px-2 py-0.5 text-[10px] font-medium uppercase`). No tooltip/badge primitive needed. Stub pages stay routable.
- Active-state matching: `pathname === href || pathname.startsWith(href + '/')` (not bare `startsWith`).
- Login redirect: replace both `ROUTES.DASHBOARD` fallbacks in `app/login/page.tsx` (lines ~28/45) with new alias `DEFAULT_AUTHENTICATED_ROUTE = ROUTES.QUIZZES` so the landing can change in one place when Home ships.

### 2. Quiz library — `/app/quizzes` (new page, the landing)

One page, two views — **not** two routes. Anatomy top-to-bottom:

1. **Header**: `h1` "Quizzes" + primary "New quiz" button (`PlusCircle`) → `/app/quiz/new`. This is the CTA's primary home.
2. **Control bar** (flex row, wraps):
   - Segmented control **My quizzes | Shared**, synced to URL `?view=shared`. No Tabs primitive exists — build with two `Button`s (`ghost`/`secondary`) in a `bg-muted rounded-md p-1` wrapper.
   - Search `Input` + `Search` icon, "Search by title or thema…", debounced (`TIMEOUTS.DEBOUNCE`), drives `?q=` server-side.
   - Filter chips (toggle `Button size='sm' variant='outline'`): **Ready** / **Generating**. No thema dropdown (free-form strings; search covers it), no difficulty filter (field doesn't exist).
3. **Card grid** `grid gap-4 sm:grid-cols-2 lg:grid-cols-3`. Each `Card`: title, thema, meta line (question count · time limit or "No limit" · type initials). Generating quizzes: `Loader2` spinner + "Generating… N%". Shared view adds owner name + `Globe` icon. Footer "Start" button (disabled while generating) → `/app/quizzes/[id]`; whole card clickable.
4. **Empty states**:
   - My quizzes, no filters: `WizardAvatar` (🧙 mascot — MUST be kept) + "No quizzes yet — let's fix that." + "Create your first quiz".
   - Shared empty: "Nobody has shared a quiz yet…"
   - Filtered empty: "No quizzes match" + "Clear filters" ghost button.
5. Pagination: "Load more" using `PAGINATION.DEFAULT_PAGE_SIZE` (20).

### 3. Quiz detail — `/app/quizzes/[id]` (new page)

- Shows title, thema, config, and **generation progress as a percentage** — never "batches" (backend vocabulary): progress bar + "Generating your questions… 50%", `% = questions_ready / questions_expected`. Secondary text "12 questions ready" once > 0.
- **Transport decision: SSE push (shipped Jul 2026, replacing the interim short polling).** The generation worker publishes each job completion to Redis pub/sub (`events:quiz-progress:{user_id}`, one channel per user); `GET /v1/quizzes/events` streams it as SSE (JWT auth, keep-alive comments); the browser's `EventSource` connects through the Next.js proxy `GET /api/quiz-events`, which attaches the bearer token (EventSource can't send Authorization headers). `useQuizEvents()` patches the react-query caches in place — detail (`['quiz', id]`) and list (`['quizzes']`) — and invalidates the list once when a quiz flips to ready. `useQuizProgress(quizId)` is now a plain query; no `refetchInterval` anywhere.
- Later this page grows: "Start quiz" (potentially startable after first batch, per generate-ahead pool design) and a share-visibility toggle.

### 4. Creation flow — kill the chooser

- **`/app/quiz/new` becomes the wizard directly.** Delete the Manual/Wizard chooser page; fold `quiz/new/wizard/` into `quiz/new/`. The chooser asked "how?" before "what?", advertised a stub, and introduced the 🧙 twice.
- The 🧙 `WizardAvatar` (`shared/components/wizard/wizard-avatar.tsx`) stays untouched — it is the identity of the creation experience.
- Manual creation: unlink from all primary UI until it exists; returns later as a quiet "Prefer to write questions yourself?" link, separate route (`/app/quiz/new/manual`).
- Wizard success bubble: use the returned quiz `id` (currently discarded in `generateMutation.onSuccess`): CTA **"Go to your quiz" → `/app/quizzes/[id]`** (replaces "Back to dashboard").

### 5. Memocards — separate section, NOT a creation mode

Flashcards are not a third option inside quiz creation. Quizzes = user-initiated adaptive tests (BKT/IRT); memocards = schedule-driven FSRS review queue, mostly auto-fed by missed answers. Deck creation (manual or AI, reusing thema-extraction + the 🧙) lives inside `/app/memocards` when built.

### 6. Home — future spec (greyed until FSRS/sessions exist)

The "what should I do today?" page; everything on it is _system-initiated_ (vs the user-initiated library). Top-to-bottom:

1. **Memory Refresh hero** — FSRS review queue (main-workflow step 3): "🧠 8 items due today" + "Start review". Empty: "All caught up."
2. **Continue/Resume strip** — in-progress sessions + still-generating quizzes (with %). Hidden when empty.
3. **Mastery snapshot** — mastered / in-progress / weak counts; 2–3 weakest concepts named with "Practice this" → wizard pre-filled with that thema.
4. **Streak & today's stats** — day streak, questions answered today, weekly accuracy. Numbers only, no badges.
5. **Quick create** — slim "Ask the 🧙 to build a new quiz" at the bottom.

Unlock order: quiz sessions → answer logging → FSRS queue → Home. Then Home becomes the landing (flip `DEFAULT_AUTHENTICATED_ROUTE`) and Quizzes moves to slot 2.

## Backend additions (question-generation-service)

- `GET /v1/quizzes?scope=mine|shared&q=&status=&page=` — list. `shared` = other users' quizzes with `visibility != 'private'` (first enforcement of the visibility column). Returns list items incl. owner display info for shared view.
- `GET /v1/quizzes/{id}` — detail + `questions_ready` / `questions_expected` (count stored questions per enqueued concept–Bloom bucket vs expected, or processed-outbox count).
- `services/quiz_service.py` + `repositories/quiz_repository.py`: list/get + progress methods.

## Frontend file-level changes (apps/web-app)

| File                                       | Change                                                                                            |
| ------------------------------------------ | ------------------------------------------------------------------------------------------------- |
| `src/app/app/quizzes/page.tsx`             | NEW — library page                                                                                |
| `src/app/app/quizzes/[id]/page.tsx`        | NEW — detail + progress                                                                           |
| `src/app/app/quiz/new/page.tsx`            | becomes the wizard (chooser deleted)                                                              |
| `src/app/app/quiz/new/wizard/`             | route removed (folded into parent)                                                                |
| `src/app/app/dashboard/`                   | delete once `/app/home` stub added                                                                |
| `src/shared/components/layout/app-nav.tsx` | `enabled` flag pattern, new item list, "Soon" pill                                                |
| `src/shared/lib/constants.ts`              | `QUIZZES`, `QUIZ_DETAIL(id)`, `HOME_APP`, `DEFAULT_AUTHENTICATED_ROUTE`; retire `QUIZ_NEW_WIZARD` |
| `src/app/login/page.tsx`                   | redirect to `DEFAULT_AUTHENTICATED_ROUTE`                                                         |
| `src/shared/lib/actions/api-client.ts`     | add `getJSON<T>`                                                                                  |
| `src/shared/lib/actions/quiz-actions.ts`   | add `listQuizzesAction`, `getQuizAction`                                                          |
| `src/shared/types/quiz.ts`                 | add `QuizListItem`, `QuizProgress` (`questions_ready`, `questions_expected`)                      |
| new components                             | `quiz-card`, `segmented-control`, `useQuizProgress` hook                                          |

## Build order

1. Backend GET endpoints (everything depends on them).
2. `/app/quizzes` library + sidebar rework + login-redirect change.
3. `/app/quizzes/[id]` detail with `useQuizProgress` polling + wizard CTA fix.
4. Delete chooser, promote wizard to `/app/quiz/new`.

After this, highest-value next feature: the **quiz session page** (users can currently create quizzes they can never take), which also unlocks SSE infra and, eventually, Home.
