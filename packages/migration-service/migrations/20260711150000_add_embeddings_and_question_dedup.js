/**
 * See docs/architecture/question-diversity-and-dedup.md for the full plan.
 *
 * Two independent guards against duplicate/near-duplicate content:
 * - `embedding` (mistral-embed, 1024-dim) on `questions` and `learning_units` —
 *   read-time cosine-similarity checks so the selection/concept-mapping
 *   services can skip candidates too close to something already served/mapped.
 * - `question_text_norm_hash`, a generated column + partial unique index on
 *   the public pool — a cheap write-time guard that stops a literal repeat
 *   generation from ever being stored, independent of the (threshold-based,
 *   slower) embedding check.
 *
 * Pre-existing exact-duplicate rows (confirmed in dev: one question_text had
 * 9 separate rows, some with real learner response history attached) would
 * block the unique index outright. Before creating it, this merges each
 * duplicate cluster onto its earliest row: real usage history (responses,
 * review queue, validation/feedback logs) is repointed, not discarded, and
 * only the now-unreferenced duplicate rows are removed.
 */
export async function up(knex) {
  await knex.raw('CREATE EXTENSION IF NOT EXISTS vector');

  await knex.raw('ALTER TABLE questions ADD COLUMN embedding vector(1024)');
  await knex.raw(
    'ALTER TABLE learning_units ADD COLUMN embedding vector(1024)'
  );

  await knex.raw(`
    CREATE INDEX idx_questions_embedding_hnsw
    ON questions USING hnsw (embedding vector_cosine_ops)
  `);
  await knex.raw(`
    CREATE INDEX idx_learning_units_embedding_hnsw
    ON learning_units USING hnsw (embedding vector_cosine_ops)
  `);

  await knex.raw(`
    ALTER TABLE questions ADD COLUMN question_text_norm_hash text
      GENERATED ALWAYS AS (md5(lower(regexp_replace(question_text, '\\s+', ' ', 'g')))) STORED
  `);

  await knex.raw(`
    CREATE TEMP TABLE question_dedup_map AS
    SELECT id AS duplicate_id,
           first_value(id) OVER (
             PARTITION BY concept_id, bloom_level, difficulty_tier, question_text_norm_hash
             ORDER BY created_at, id
           ) AS canonical_id
    FROM questions
    WHERE owner_user_id IS NULL
  `);
  await knex.raw(
    'DELETE FROM question_dedup_map WHERE duplicate_id = canonical_id'
  );

  await knex.raw(`
    UPDATE user_responses ur SET question_id = m.canonical_id
    FROM question_dedup_map m WHERE ur.question_id = m.duplicate_id
  `);
  await knex.raw(`
    UPDATE review_queue rq SET question_id = m.canonical_id
    FROM question_dedup_map m WHERE rq.question_id = m.duplicate_id
  `);
  await knex.raw(`
    UPDATE review_queue_archive rqa SET question_id = m.canonical_id
    FROM question_dedup_map m WHERE rqa.question_id = m.duplicate_id
  `);
  await knex.raw(`
    UPDATE question_validation_log qvl SET question_id = m.canonical_id
    FROM question_dedup_map m WHERE qvl.question_id = m.duplicate_id
  `);
  await knex.raw(`
    UPDATE question_feedback_log qfl SET question_id = m.canonical_id
    FROM question_dedup_map m WHERE qfl.question_id = m.duplicate_id
  `);
  // question_serving_log's PK is (user_id, question_id) — repointing can
  // collide not only against the canonical row's own log entry, but against
  // a *sibling* duplicate row for the same user in the same cluster (a user
  // served two different duplicate copies of the same question). Both cases
  // are "the same user already has a log entry for this canonical id" once
  // duplicates are mapped through question_dedup_map, so drop every row that
  // isn't the earliest such entry — whether the earlier one lives on the
  // canonical row or on another duplicate — before repointing what's left.
  await knex.raw(`
    DELETE FROM question_serving_log qsl
    USING question_dedup_map m
    WHERE qsl.question_id = m.duplicate_id
      AND EXISTS (
        SELECT 1 FROM question_serving_log qsl2
        LEFT JOIN question_dedup_map m2 ON qsl2.question_id = m2.duplicate_id
        WHERE qsl2.user_id = qsl.user_id
          AND COALESCE(m2.canonical_id, qsl2.question_id) = m.canonical_id
          AND (qsl2.served_at, qsl2.question_id) < (qsl.served_at, qsl.question_id)
      )
  `);
  await knex.raw(`
    UPDATE question_serving_log qsl SET question_id = m.canonical_id
    FROM question_dedup_map m WHERE qsl.question_id = m.duplicate_id
  `);

  await knex.raw(
    'DELETE FROM questions WHERE id IN (SELECT duplicate_id FROM question_dedup_map)'
  );
  await knex.raw('DROP TABLE question_dedup_map');

  await knex.raw(`
    CREATE UNIQUE INDEX idx_questions_concept_text_dedup
    ON questions (concept_id, bloom_level, difficulty_tier, question_text_norm_hash)
    WHERE owner_user_id IS NULL
  `);
}

export async function down(knex) {
  await knex.raw('DROP INDEX IF EXISTS idx_questions_concept_text_dedup');
  await knex.raw(
    'ALTER TABLE questions DROP COLUMN IF EXISTS question_text_norm_hash'
  );
  await knex.raw('DROP INDEX IF EXISTS idx_learning_units_embedding_hnsw');
  await knex.raw('DROP INDEX IF EXISTS idx_questions_embedding_hnsw');
  await knex.raw('ALTER TABLE learning_units DROP COLUMN IF EXISTS embedding');
  await knex.raw('ALTER TABLE questions DROP COLUMN IF EXISTS embedding');
  // Extension left in place, and the duplicate-merge above is not reversed —
  // both are standard for a cleanup migration; DROP EXTENSION is a manual
  // step once nothing else depends on it.
}
