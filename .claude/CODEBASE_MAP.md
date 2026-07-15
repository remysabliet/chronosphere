# Codebase Map

Purpose: locate code without exploratory searching. Read the target file before editing, but do not re-scan the repo layout. Update this map when adding/moving a module or directory.

## Monorepo layout (pnpm workspace)

| Path | What it is |
|---|---|
| `apps/web-app` | Next.js 15 App Router frontend (the only app) |
| `packages/question-generation-service` | Python/FastAPI — MAIN backend: quizzes, sessions, questions, themas, BKT/adaptive logic |
| `packages/learning-engine-service` | Python/FastAPI (poetry) — minimal, only `main.py` so far |
| `packages/migration-service` | Knex migrations (`migrations/`, numbered) + `seeds/`; DB schema source of truth |
| `packages/shared-python` | `memosphere_auth` (Cognito), `memosphere_domain`, `memosphere_messaging` |
| `packages/shared-typescript` | `cognito-auth.ts`, `domain.ts`, `messaging.ts` |
| `packages/{analytics,content-management,notification,quiz-session,user-management}-service` | STUBS (only `src/index.ts`) — do not add code here unless asked |
| `infrastructure/docker` | `docker-compose.yml` (postgres, redis); `data/` is runtime volumes — never touch |
| `docs/architecture` | `db-schema.md`, `infra-architecture.md`, mistral strategy, per-stack pattern docs |
| `docs/product` | `mvp.md`, `mvp-planning.md`, `functional/` |
| `docs/dev/code-review-checklist.md` | review checklist referenced by CLAUDE.md |
| `tools/`, `scripts/` | repo tooling/config; `tests/` at root = cross-cutting e2e/unit |

Root configs: `eslint.config.js`, `prettier.config.js`, `ruff.toml`, `tsconfig.json`, `vitest*.config.js`, `playwright.config.js`, `pnpm-workspace.yaml`.

## Frontend — `apps/web-app/src`

Routes (`app/`):
- `(public)/` — marketing pages (landing, about, features, pricing, demo, privacy, terms) + own `layout.tsx`
- `login/page.tsx` — auth entry; `api/auth/[...nextauth]/route.ts` — NextAuth (Cognito)
- `app/` — authenticated area (`layout.tsx` = app shell/nav): `home`, `quizzes` (list), `quizzes/[id]` (detail), `quiz/new` (creation wizard), `quiz/new/manual`, `sessions/[id]` (quiz taking), `history` (global session history, by-date/by-quiz views), `analytics`, `memocards`, `profile`

Shared (`shared/`):
- `lib/actions/` — server actions + backend calls: `api-client.ts` (fetch wrapper, auth headers), `quiz-actions.ts`, `session-actions.ts`, `thema-actions.ts`. New backend call → action file here via `api-client`.
- `lib/` — `auth.ts` (NextAuth config), `constants.ts` (routes/URLs/config), `errors.ts`, `utils.ts`
- `components/ui/` — primitives (button, card, input, alert-dialog…; barrel `index.ts`)
- `components/quiz/` — quiz-domain components; `components/wizard/` — quiz-creation wizard (wizard-avatar 🧙 = protected mascot); `components/layout/` — nav/header/footer; `components/auth/`, `components/providers/` (react-query)
- `hooks/` — `use-quiz-progress`, `use-delete-quiz`, `use-copy-quiz`, `use-debounced-value`; new client data logic → hook here
- `types/` — `quiz.ts`, `session.ts`, `thema.ts`, `next-auth.d.ts`

## Backend — `packages/question-generation-service/src/question_generation_service`

Layering: router → service → repository → model. New endpoint touches, in order: `schemas/` (pydantic I/O) → `routers/` → `services/` → `repositories/` (+ `models/` if new table).

- `routers/` — `quiz`, `session`, `questions`, `thema`, `concept`, `wizard`, `moderation`
- `services/` — business logic: `quiz`, `session`, `question`, `thema`, `wizard`, `concept`, `adaptive_selection` (IRT pick), `bkt_init`, `mastery` (BKT updates), `exposure`, `question_validation`
- `repositories/` — SQLAlchemy queries per aggregate (quiz, session, question, thema, learning_unit, exposure, concept_progress, bkt_parameters, user)
- `models/` — SQLAlchemy tables; `schemas/` — pydantic DTOs
- `prompts/` — LLM prompt builders: `question_generation`, `question_judge`, `concept_map`, `thema_topic_extract`, `quiz_length_interpret`
- `clients/` — Mistral LLM client + transport/config
- `workers/` — `generation_worker` (async question gen), `outbox_relay`
- `dependencies/` — FastAPI DI: `auth`, `rate_limit`, `services` (wiring), `user_provisioning`
- `core/` — `config.py` (settings/env), `exceptions.py`; `db/` — engine/session/base

## Conventions
- DB change → new migration in `packages/migration-service/migrations` (never edit old ones)
- Auth: Cognito everywhere — frontend via NextAuth + `shared-typescript/cognito-auth`, backend via `memosphere_auth` + `dependencies/auth.py`
- No `Any` types; strict typing both languages
