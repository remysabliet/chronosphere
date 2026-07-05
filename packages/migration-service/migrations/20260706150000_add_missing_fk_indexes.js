/**
 * Schema scale review: Postgres never auto-indexes FK columns. Several
 * concept_id/question_id foreign keys had no covering index of their own,
 * so an ON DELETE CASCADE (or any query scoped by that column alone) falls
 * back to a sequential scan. learning_path_log had no indexes at all.
 */
export async function up(knex) {
  await knex.schema.alterTable('learning_path_log', table => {
    table.index(['user_id', 'concept_id', 'bloom_level']);
    table.index(['concept_id']);
  });
  await knex.schema.alterTable('user_responses', table => {
    table.index(['concept_id']);
  });
  await knex.schema.alterTable('mastery_log', table => {
    table.index(['concept_id']);
  });
  await knex.schema.alterTable('review_queue', table => {
    table.index(['question_id']);
  });
  await knex.schema.alterTable('review_queue_archive', table => {
    table.index(['question_id']);
  });
}

export async function down(knex) {
  await knex.schema.alterTable('review_queue_archive', table => {
    table.dropIndex(['question_id']);
  });
  await knex.schema.alterTable('review_queue', table => {
    table.dropIndex(['question_id']);
  });
  await knex.schema.alterTable('mastery_log', table => {
    table.dropIndex(['concept_id']);
  });
  await knex.schema.alterTable('user_responses', table => {
    table.dropIndex(['concept_id']);
  });
  await knex.schema.alterTable('learning_path_log', table => {
    table.dropIndex(['concept_id']);
    table.dropIndex(['user_id', 'concept_id', 'bloom_level']);
  });
}
