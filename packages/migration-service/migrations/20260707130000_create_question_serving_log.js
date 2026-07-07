/**
 * Tracks which stored questions a given user has already been served, so the
 * pool-reuse path in question-generation-service can prefer unseen questions
 * for that user before falling back to generating new ones (or, as a last
 * resort, repeating something they've already seen). Deliberately separate
 * from `user_responses` — that table is for actual answers on the future
 * quiz-taking loop; this one only answers "have we shown this to them before."
 */
export async function up(knex) {
  await knex.schema.createTable('question_serving_log', table => {
    table.uuid('user_id').notNullable();
    table.uuid('question_id').notNullable();
    table.timestamp('served_at').notNullable().defaultTo(knex.fn.now());

    table.primary(['user_id', 'question_id']);

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

    table.index(['user_id']);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('question_serving_log');
}
