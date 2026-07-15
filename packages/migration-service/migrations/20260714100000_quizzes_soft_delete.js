/**
 * Quiz deletion becomes a soft delete: a learner's session history (and its
 * per-question review) must outlive the quiz config it ran against, but the
 * old quiz_sessions.quiz_id FK cascaded and erased it. deleted_at tombstones
 * the quiz instead — listings hide it, history keeps its title and review.
 *
 * The FK moves to ON DELETE SET NULL as a backstop: nothing hard-deletes
 * quizzes today, but a future retention/purge job (or GDPR erasure) must
 * never take session rows down with it.
 *
 * Index changes, sized for the two hot per-user queries:
 * - quiz listings only ever read live rows → the (owner, updated_at) index
 *   becomes partial on deleted_at IS NULL, so tombstones never bloat it.
 * - the History page reads user_id ORDER BY start_time DESC LIMIT n → one
 *   composite index serves it; the single-column user_id index it makes
 *   redundant (leftmost prefix) is dropped.
 */
export async function up(knex) {
  await knex.schema.alterTable('quizzes', table => {
    table.timestamp('deleted_at', { useTz: true });
  });

  await knex.raw(`
    ALTER TABLE quiz_sessions
    DROP CONSTRAINT quiz_sessions_quiz_id_foreign
  `);
  await knex.raw(`
    ALTER TABLE quiz_sessions
    ADD CONSTRAINT quiz_sessions_quiz_id_foreign
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE SET NULL
  `);

  await knex.raw('DROP INDEX idx_quizzes_owner_recent');
  await knex.raw(`
    CREATE INDEX idx_quizzes_owner_recent
    ON quizzes(owner_user_id, updated_at)
    WHERE deleted_at IS NULL
  `);

  await knex.schema.alterTable('quiz_sessions', table => {
    table.dropIndex(['user_id']);
  });
  await knex.raw(`
    CREATE INDEX idx_quiz_sessions_user_recent
    ON quiz_sessions(user_id, start_time DESC)
  `);
}

export async function down(knex) {
  await knex.raw('DROP INDEX idx_quiz_sessions_user_recent');
  await knex.schema.alterTable('quiz_sessions', table => {
    table.index(['user_id']);
  });

  await knex.raw('DROP INDEX idx_quizzes_owner_recent');
  await knex.raw(`
    CREATE INDEX idx_quizzes_owner_recent
    ON quizzes(owner_user_id, updated_at)
  `);

  await knex.raw(`
    ALTER TABLE quiz_sessions
    DROP CONSTRAINT quiz_sessions_quiz_id_foreign
  `);
  await knex.raw(`
    ALTER TABLE quiz_sessions
    ADD CONSTRAINT quiz_sessions_quiz_id_foreign
    FOREIGN KEY (quiz_id) REFERENCES quizzes(id) ON DELETE CASCADE
  `);

  await knex.schema.alterTable('quizzes', table => {
    table.dropColumn('deleted_at');
  });
}
