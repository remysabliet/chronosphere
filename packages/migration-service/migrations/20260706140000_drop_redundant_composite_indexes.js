/**
 * Schema scale review: concept_progress_tracker, mastery_log, and review_queue
 * each carry an explicit btree index on the exact same columns as their
 * composite primary key. The PK already is that index — the extra one is
 * write overhead (every insert maintains it) with zero query benefit.
 */
export async function up(knex) {
  await knex.schema.alterTable('concept_progress_tracker', table => {
    table.dropIndex(['user_id', 'concept_id', 'bloom_level']);
  });
  await knex.schema.alterTable('mastery_log', table => {
    table.dropIndex(['user_id', 'concept_id', 'bloom_level']);
  });
  await knex.schema.alterTable('review_queue', table => {
    table.dropIndex(['user_id', 'concept_id', 'bloom_level']);
  });
}

export async function down(knex) {
  await knex.schema.alterTable('review_queue', table => {
    table.index(['user_id', 'concept_id', 'bloom_level']);
  });
  await knex.schema.alterTable('mastery_log', table => {
    table.index(['user_id', 'concept_id', 'bloom_level']);
  });
  await knex.schema.alterTable('concept_progress_tracker', table => {
    table.index(['user_id', 'concept_id', 'bloom_level']);
  });
}
