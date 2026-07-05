/**
 * Schema scale review: standalone indexes on booleans/small enums give the
 * planner almost no selectivity at scale (it will pick a scan over them
 * anyway) while still costing a write on every insert. Dropping them; the
 * columns remain queryable, just without a dedicated index.
 */
export async function up(knex) {
  await knex.schema.alterTable('user_responses', table => {
    table.dropIndex(['is_correct']);
    table.dropIndex(['decision_type']);
  });
  await knex.schema.alterTable('question_feedback_log', table => {
    table.dropIndex(['rating']);
    table.dropIndex(['flag_reason']);
  });
}

export async function down(knex) {
  await knex.schema.alterTable('question_feedback_log', table => {
    table.index(['rating']);
    table.index(['flag_reason']);
  });
  await knex.schema.alterTable('user_responses', table => {
    table.index(['is_correct']);
    table.index(['decision_type']);
  });
}
