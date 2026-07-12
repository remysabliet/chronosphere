/**
 * Redelivery of a jobs:generate-questions message (crash/timeout between the
 * worker finishing generation and acking the stream entry) must not re-run
 * quiz_repository.increment_questions_ready — that column has no other way
 * to tell "already counted" from "brand new" apart. This table is the claim
 * check: the worker inserts the stream message_id before incrementing, and
 * only increments if the insert actually happened (ON CONFLICT DO NOTHING).
 */
export async function up(knex) {
  await knex.schema.createTable('generation_job_completions', table => {
    table.string('message_id').primary();
    table
      .timestamp('completed_at', { useTz: true })
      .notNullable()
      .defaultTo(knex.fn.now());
  });
}

export async function down(knex) {
  await knex.schema.dropTable('generation_job_completions');
}
