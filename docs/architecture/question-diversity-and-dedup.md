# Question Diversity & Concept Dedup — Plan (2026-07-11)

## Problem

Confirmed via direct DB query against `memosphere_development`: the `questions` table contains
many rows with byte-identical `question_text` but different `id`. One string existed as **9**
separate rows. At least one duplicate spanned two different `concept_id`s. A learner could be
served two near/exact-duplicate questions in the same quiz — the "already served" filter
(`question_serving_log`) only excludes by exact row `id`, never by content.

Two compounding root causes, found by two independent investigations:

1. **Question generation has no dedup anywhere.** `QuestionRepository.save_batch` is an
   unconditional insert. The generation prompt (Prompt 3) has no memory of what was already
   generated for a given concept/bloom/tier cell in a previous call — temperature 0.5, no
   `random_seed` variation, no "avoid repeating X" context. A concept's pre-generated pool is
   small (`BATCH_SIZE=5`) and exhausts fast once a learner has seen those, forcing live
   regeneration (`AdaptiveSelectionService._generate_live`) with the same narrow prompt inputs
   repeatedly — which is also why "AI on every answer" was happening more than intended.

2. **Concept creation dedups on the wrong, non-deterministic field.** `ConceptService.map()`
   matches on `topic` — Prompt 1's freeform extraction, which is not guaranteed to phrase "the
   same" subject identically across calls ("Variables" vs "Variable Declaration"). Re-exploring
   a thema silently fails to reuse existing concepts and mints a new near-duplicate concept row
   instead, which then independently generates its own "unique" but content-duplicate questions.

## Decision

Use embeddings (`mistral-embed`, via the same Mistral SDK/API key already in use) for both
problems, backed by `pgvector`, instead of two different techniques (hash + trigram):

- **Questions**: embed `question_text` at generation time. At selection time, exclude candidates
  whose embedding is cosine-similar (above a threshold) to anything already served to this user —
  extends the existing user-scoped "already served" filter rather than introducing a new
  session-scoped concept.
- **Concepts**: embed `concept_name` at creation time. Before inserting a new concept for a
  thema, check similarity against existing concepts for that thema; reuse the existing row above
  threshold instead of minting a duplicate.
- **Kept as a cheap complementary safety net**: an exact-match guard (normalized-text hash +
  partial unique index) on `questions`, so a literal repeat from the LLM never even gets stored —
  avoids storage/generation waste independent of the (slower, threshold-based) embedding check.

Rejected: trigram (`pg_trgm`) similarity — surface-text only, doesn't catch paraphrases
("cannot be reassigned after initialization" vs "...once initialized" — same fact, different
words). Embeddings are a superset: they catch trigram's cases too, via one new dependency
instead of two different techniques in two places.

## Performance: embedding calls must not slow generation down

Chat completion models and embedding models are architecturally different — a completion
response never carries an embedding as a byproduct; embeddings always require a separate API
call. Two things keep this cheap:

- **Batched, not per-question**: the embeddings endpoint takes a list of texts in one request —
  one call per generation batch (up to `BATCH_SIZE=5` questions), not one call per question.
- **Parallel, not sequential**: the embedding call only needs the Prompt-3 drafts (after
  structural validation), same as the Prompt 4 judge call — neither depends on the other's
  output. Run them concurrently (`asyncio.gather`) so the embedding call is hidden behind the
  judge call's latency instead of adding to the pipeline's wall-clock time.

## Implementation

1. **Infra**: swap `postgres:17-alpine` → `pgvector/pgvector:pg17` in
   `infrastructure/docker/docker-compose.yml` (drop-in — same Postgres 17, extension
   pre-compiled in).
2. **Migration**: `CREATE EXTENSION vector;` — add `embedding vector(1024)` to `questions` and
   `learning_units`; add a generated `question_text_norm_hash` column + partial unique index on
   `questions (concept_id, bloom_level, difficulty_tier, question_text_norm_hash) WHERE
owner_user_id IS NULL`.
3. **`clients/mistral_client.py`**: new `embed(texts: list[str]) -> list[list[float]]` using
   `client.embeddings.create_async(model="mistral-embed", inputs=texts)`, alongside the existing
   `chat_complete`.
4. **`services/question_service.py`**: in `_generate_new`, after structural validation, run
   `_judge_batch(...)` and `embed(...)` concurrently via `asyncio.gather` over the same
   structurally-valid candidate set; pass the resulting vectors into `save_batch`.
5. **`repositories/question_repository.py`**: `save_batch` accepts embeddings, inserts with
   `ON CONFLICT (concept_id, bloom_level, difficulty_tier, question_text_norm_hash)
WHERE owner_user_id IS NULL DO NOTHING`. `get_candidates`/`get_pool_for_session` gain a
   cosine-distance exclusion (pgvector `<=>`) against the embeddings of everything already served
   to this user (join through `question_serving_log`).
6. **`services/concept_service.py`** + **`repositories/learning_unit_repository.py`**: embed each
   Prompt-2 candidate's `concept_name`; before inserting, look up the most similar existing
   concept for the thema (pgvector `<=>`); reuse above threshold instead of inserting.
7. **`services/quiz_service.py`**: `create()`'s bucket selection currently exhausts one concept's
   bloom ladder before moving to the next (`pairs = [(unit, bloom) for unit in units for bloom in
...]`, then `pairs[:batches_needed]`) — switch to round-robin across units so pre-generation
   spreads across distinct concepts instead of clustering on the first 1-2 returned.

## Explicitly deferred (not part of this change)

Cleaning up the ~100+ duplicate concepts already sitting in the dev DB. `concept_progress_tracker`
and `review_queue` have composite PKs including `concept_id` — merging is not a simple `UPDATE`,
it's combine-attempt-counts-then-repoint-then-delete per cluster, with real conflict handling.
Needs its own dry-run-capable script, reviewed separately once the prevention fix is verified
working.

## Status — done 2026-07-11

- [x] Postgres image swap (`pgvector/pgvector:0.8.5-pg17-bookworm`)
- [x] Migration (extension, embedding columns, hash + unique index) — applied to
      dev and test, with a safe duplicate-merge (repoints response/serving/
      review-queue history onto the canonical row rather than deleting it)
- [x] `embed()` helper (`clients/mistral_client.py`)
- [x] Generation-time embedding, run concurrently with the judge call via
      `asyncio.gather` (`services/question_service.py`)
- [x] Question repository: write-time hash dedup (`ON CONFLICT DO NOTHING`) +
      read-time similarity exclusion (`_not_too_similar_condition`)
- [x] Concept service + repository: embedding-based dedup
      (`find_similar_concept`, cosine distance via pgvector)
- [x] Quiz bucket round-robin (`_round_robin_pairs`)
- [x] Tests updated across all touched modules (194 passing, stable across
      repeated runs)
- [x] Full suite green; verified against a real Mistral API + real Postgres
      run (`test_live_ai_pipeline.py`) — generation, judging, and embedding all
      completed without error; separately verified by direct query that (a)
      embeddings round-trip correctly through pgvector, (b) the write-time
      hash guard actually skips a literal repeat, and (c) the read-time
      similarity check excludes near-duplicate content while still offering
      genuinely different questions

Known residual: exact-duplicate `questions` rows that span _different_
`concept_id`s (from concept duplication that predates this fix) were not
merged by this migration — the write-time hash guard is scoped per-concept
deliberately, to not fight the concept-dedup fix. These are no longer served
as duplicates going forward (the read-time embedding check is concept-
agnostic), but the rows themselves remain until the deferred concept-merge
cleanup (see above) runs.
