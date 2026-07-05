/**
 * Same issue as questions.options (see questions_options_jsonb.js): json
 * re-parses stored text on every read, jsonb is binary and indexable, and
 * nothing here needs exact text preservation.
 */
const QUIZ_SESSIONS_COLUMNS = [
  'difficulty_progression',
  'bloom_level_distribution',
  'session_goals',
  'confidence_trend',
  'mastery_gains',
];
const MASTERY_LOG_COLUMNS = ['usage_stats', 'fsrs_state'];

export async function up(knex) {
  for (const column of QUIZ_SESSIONS_COLUMNS) {
    await knex.raw(
      `ALTER TABLE quiz_sessions ALTER COLUMN ?? TYPE jsonb USING ??::jsonb`,
      [column, column]
    );
  }
  for (const column of MASTERY_LOG_COLUMNS) {
    await knex.raw(
      `ALTER TABLE mastery_log ALTER COLUMN ?? TYPE jsonb USING ??::jsonb`,
      [column, column]
    );
  }
}

export async function down(knex) {
  for (const column of MASTERY_LOG_COLUMNS) {
    await knex.raw(
      `ALTER TABLE mastery_log ALTER COLUMN ?? TYPE json USING ??::json`,
      [column, column]
    );
  }
  for (const column of QUIZ_SESSIONS_COLUMNS) {
    await knex.raw(
      `ALTER TABLE quiz_sessions ALTER COLUMN ?? TYPE json USING ??::json`,
      [column, column]
    );
  }
}
