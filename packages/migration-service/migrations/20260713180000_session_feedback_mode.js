/**
 * Feedback timing is a per-session learner choice (immediate | end | never):
 * quiz_sessions.feedback_mode freezes the choice for the run so redaction
 * stays consistent even if the user's preference changes mid-session;
 * users.default_feedback_mode remembers the last explicit choice and
 * pre-selects it on the next quiz start.
 */
export async function up(knex) {
  await knex.schema.alterTable('quiz_sessions', table => {
    table.text('feedback_mode').notNullable().defaultTo('end');
  });
  await knex.schema.alterTable('users', table => {
    table.text('default_feedback_mode').notNullable().defaultTo('end');
  });
}

export async function down(knex) {
  await knex.schema.alterTable('quiz_sessions', table => {
    table.dropColumn('feedback_mode');
  });
  await knex.schema.alterTable('users', table => {
    table.dropColumn('default_feedback_mode');
  });
}
