/**
 * quiz_sessions predates the quizzes table and had no way to link a session
 * back to the quiz config it's a run of. quiz_id closes that gap; question_ids
 * freezes the ordered set of questions served for this session at start time,
 * so answering out of order or re-fetching mid-session is still consistent
 * even as the underlying pool keeps growing in the background.
 */
export async function up(knex) {
  await knex.schema.alterTable('quiz_sessions', table => {
    table.uuid('quiz_id');
    table.specificType('question_ids', 'UUID[]').notNullable().defaultTo('{}');
    table
      .foreign('quiz_id')
      .references('id')
      .inTable('quizzes')
      .onDelete('CASCADE');
    table.index(['quiz_id', 'user_id']);
  });
}

export async function down(knex) {
  await knex.schema.alterTable('quiz_sessions', table => {
    table.dropIndex(['quiz_id', 'user_id']);
    table.dropForeign(['quiz_id']);
    table.dropColumn('question_ids');
    table.dropColumn('quiz_id');
  });
}
