---
name: verify
description: How to run and drive Memosphere locally to verify changes end-to-end (auth bypass, seeding, Playwright driving).
---

# Verifying Memosphere changes at runtime

## Stack handle

Everything runs via docker compose from `infrastructure/docker/`; backend
(`memosphere-question-generation`, :8001) and web-app (`memosphere-web-app`,
:3000) volume-mount `src/` with hot reload — code changes apply without
rebuild. Exception: new files in `packages/migration-service/migrations/` need
`docker compose build migration-service` (migrations are baked into that
image) or `pnpm migrate:latest` run on the host from that package.

## Auth (Cognito) — dev bypass

Real Cognito tokens are required by default; there are no test credentials.
For local verification use the bypass flag (default off):

```bash
cd infrastructure/docker
DEV_AUTH_BYPASS=true docker compose up -d question-generation-service web-app
```

- Backend then serves a fixed user `00000000-0000-4000-8000-000000000001`
  (`dev-bypass@local.test`) for every request — curl works with no token.
- Frontend gains a hidden NextAuth credentials provider `dev-bypass`.
  Log in programmatically (no UI): GET `/api/auth/csrf`, then POST
  `/api/auth/callback/dev-bypass` with `{ csrfToken }` as form body; the
  session cookie is then set for the browser context.
- **Turn it off after**: rerun the same `up -d` without the env var, then
  confirm `curl -s -o /dev/null -w '%{http_code}' localhost:8001/v1/me/session-preferences` → 401.

## Seeding a playable quiz without LLM calls

A fresh user can't start quizzes (no BKT rows → adaptive selection returns
none). Seed against an existing thema's question pool (e.g. `Cooking`):

```sql
-- psql: docker exec memosphere-postgres-development psql -U memosphere -d memosphere_development
INSERT INTO quizzes (id, owner_user_id, thema, title, question_types, question_count,
  visibility, generation_questions_ready, generation_jobs_total, generation_jobs_completed)
VALUES ('<quiz-uuid>', '<user-uuid>', 'Cooking', 'Verify Cooking',
  '{FillInBlank,TrueFalse}', 3, 'private', 23, 1, 1);

INSERT INTO concept_progress_tracker (user_id, concept_id, bloom_level,
  attempt_count, correct_count, slip_count, mastery_status, p_ln)
SELECT '<user-uuid>', cp.concept_id, cp.bloom_level, 0, 0, 0, 'In Progress', 0.2
FROM (SELECT DISTINCT concept_id, bloom_level FROM concept_progress_tracker cpt
      JOIN learning_units lu ON lu.id = cpt.concept_id WHERE lu.thema = 'Cooking') cp
ON CONFLICT DO NOTHING;
```

To answer deterministically, dump an answer key first:
`SELECT json_object_agg(question_text, correct_answers) FROM questions q JOIN
learning_units lu ON lu.id = q.concept_id WHERE lu.thema = 'Cooking';`

## Driving the GUI

Playwright is available at the repo root (`node_modules/playwright`). Flows:
quizzes list `/app/quizzes` → quiz detail `/app/quizzes/<id>` (feedback-mode
selector + Start) → session `/app/sessions/<id>` → results render in place on
completion. Question inputs: FillInBlank = `input[placeholder="Type your
answer…"]`; TrueFalse = option buttons. Backend can also be curl'd directly
on :8001 while the bypass is on.

## Gotchas

- Never run generation/wizard flows in verification — they call Mistral
  (cost). Seeded pools + session/review endpoints make zero LLM calls.
- `docker compose up` waits on `migration-service` completing; if it exits 1
  with "migration directory is corrupt", rebuild its image (stale migrations).
- Don't touch `infrastructure/docker/data/` (runtime volumes).
