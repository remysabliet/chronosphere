/**
 * The generation worker increments this counter as each jobs:generate-questions
 * batch enqueued by a quiz completes — GET /v1/quizzes/{id} reports it against
 * the quiz's expected count so the UI can show real generation progress instead
 * of polling batch internals.
 */
export async function up(knex) {
  await knex.schema.alterTable('quizzes', table => {
    table.integer('generation_questions_ready').notNullable().defaultTo(0);
  });
}

export async function down(knex) {
  await knex.schema.alterTable('quizzes', table => {
    table.dropColumn('generation_questions_ready');
  });
}
