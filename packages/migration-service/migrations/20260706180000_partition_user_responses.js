/**
 * Schema scale review, item 5: user_responses is the only genuinely
 * unbounded, high-velocity table (one row per answer, ever) — range-
 * partitioning it by timestamp now, while it's empty, avoids a much harder
 * online migration later. Monthly partitions, plus a DEFAULT catch-all.
 *
 * Postgres requires the partition key in every unique/PK constraint, so the
 * primary key becomes (id, timestamp) instead of (id) alone. That means
 * question_feedback_log.response_id can no longer FK a column that isn't
 * uniquely enforced across all partitions — id alone no longer qualifies.
 * The constraint is dropped; that link is now application-enforced only.
 *
 * This migration only bootstraps the initial partitions. Creating new
 * monthly partitions ahead of time needs an ongoing job (e.g. pg_partman or
 * a scheduled task) — not handled here.
 */

const MONTH_STARTS = [
  '2026-06-01',
  '2026-07-01',
  '2026-08-01',
  '2026-09-01',
  '2026-10-01',
  '2026-11-01',
  '2026-12-01',
  '2027-01-01',
];

export async function up(knex) {
  await knex.raw(
    'ALTER TABLE question_feedback_log DROP CONSTRAINT IF EXISTS question_feedback_log_response_id_foreign'
  );

  // Empty in every environment today (no ORM model or writer exists yet for
  // this table) — recreate as partitioned rather than an online data migration.
  await knex.schema.dropTableIfExists('user_responses');

  await knex.raw(`
    CREATE TABLE user_responses (
      id uuid NOT NULL,
      session_id uuid,
      user_id uuid NOT NULL,
      question_id uuid NOT NULL,
      concept_id uuid NOT NULL,
      bloom_level varchar(255) NOT NULL,
      selected_option varchar(255),
      is_correct boolean,
      confidence_level varchar(255),
      response_time integer,
      decision_type varchar(255),
      "timestamp" timestamptz NOT NULL,
      attempt_quality varchar(255),
      question_sequence_order integer,
      PRIMARY KEY (id, "timestamp"),
      CONSTRAINT chk_user_responses_decision_type
        CHECK (decision_type IN ('Review', 'Practice', 'Advance', 'Remediate')),
      CONSTRAINT user_responses_confidence_level_check
        CHECK (confidence_level IN ('Low', 'Medium', 'High')),
      CONSTRAINT user_responses_session_id_foreign
        FOREIGN KEY (session_id) REFERENCES quiz_sessions (session_id) ON DELETE SET NULL,
      CONSTRAINT user_responses_user_id_foreign
        FOREIGN KEY (user_id) REFERENCES users (user_id) ON DELETE CASCADE,
      CONSTRAINT user_responses_question_id_foreign
        FOREIGN KEY (question_id) REFERENCES questions (id) ON DELETE CASCADE,
      CONSTRAINT user_responses_concept_id_foreign
        FOREIGN KEY (concept_id) REFERENCES learning_units (id) ON DELETE CASCADE
    ) PARTITION BY RANGE ("timestamp");
  `);

  // Created once on the parent — Postgres propagates each to every partition
  // (current and future) automatically.
  await knex.raw(
    'CREATE INDEX user_responses_user_id_concept_id_bloom_level_index ON user_responses (user_id, concept_id, bloom_level)'
  );
  await knex.raw(
    'CREATE INDEX user_responses_concept_id_index ON user_responses (concept_id)'
  );
  await knex.raw(
    'CREATE INDEX user_responses_question_id_index ON user_responses (question_id)'
  );
  await knex.raw(
    'CREATE INDEX user_responses_timestamp_index ON user_responses ("timestamp")'
  );
  await knex.raw(
    'CREATE INDEX user_responses_user_id_is_correct_timestamp_index ON user_responses (user_id, is_correct, "timestamp")'
  );
  await knex.raw(
    'CREATE INDEX user_responses_session_id_index ON user_responses (session_id)'
  );

  for (let i = 0; i < MONTH_STARTS.length - 1; i++) {
    const start = MONTH_STARTS[i];
    const end = MONTH_STARTS[i + 1];
    const suffix = start.slice(0, 7).replace('-', '_');
    await knex.raw(
      `CREATE TABLE user_responses_${suffix} PARTITION OF user_responses FOR VALUES FROM ('${start}') TO ('${end}')`
    );
  }
  await knex.raw(
    'CREATE TABLE user_responses_default PARTITION OF user_responses DEFAULT'
  );
}

export async function down(knex) {
  await knex.schema.dropTableIfExists('user_responses');

  await knex.schema.createTable('user_responses', table => {
    table.uuid('id').primary();
    table.uuid('session_id');
    table.uuid('user_id').notNullable();
    table.uuid('question_id').notNullable();
    table.uuid('concept_id').notNullable();
    table.string('bloom_level').notNullable();
    table.string('selected_option');
    table.boolean('is_correct');
    table.string('confidence_level');
    table.integer('response_time');
    table.string('decision_type');
    table.timestamp('timestamp').notNullable();
    table.string('attempt_quality');
    table.integer('question_sequence_order');

    table
      .foreign('session_id')
      .references('session_id')
      .inTable('quiz_sessions')
      .onDelete('SET NULL');
    table
      .foreign('user_id')
      .references('user_id')
      .inTable('users')
      .onDelete('CASCADE');
    table
      .foreign('question_id')
      .references('id')
      .inTable('questions')
      .onDelete('CASCADE');
    table
      .foreign('concept_id')
      .references('id')
      .inTable('learning_units')
      .onDelete('CASCADE');

    table.index(['user_id', 'concept_id', 'bloom_level']);
    table.index(['concept_id']);
    table.index(['question_id']);
    table.index(['timestamp']);
    table.index(['user_id', 'is_correct', 'timestamp']);
    table.index(['session_id']);

    table.check('decision_type IN (?, ?, ?, ?)', [
      'Review',
      'Practice',
      'Advance',
      'Remediate',
    ]);
    table.check('confidence_level IN (?, ?, ?)', ['Low', 'Medium', 'High']);
  });

  await knex.raw(`
    ALTER TABLE question_feedback_log
    ADD CONSTRAINT question_feedback_log_response_id_foreign
    FOREIGN KEY (response_id) REFERENCES user_responses (id) ON DELETE CASCADE
  `);
}
