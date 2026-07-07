/**
 * Questions generated from a user's private documents must never be served
 * to anyone else. owner_user_id = NULL means public shared pool (all existing
 * rows); non-NULL means private to that user. Partial indexes keep each pool's
 * index containing only its own rows, so public scans never touch private
 * entries and vice versa. Also sheds two redundant indexes:
 * - questions(concept_id, bloom_level): pure prefix of idx_questions_tier
 * - question_serving_log(user_id): pure prefix of its PK (user_id, question_id)
 * and adds the missing FK index on question_serving_log.question_id
 * (questions deletes cascade into the log).
 */
export async function up(knex) {
  await knex.schema.alterTable('questions', table => {
    table.uuid('owner_user_id');
    table
      .foreign('owner_user_id')
      .references('user_id')
      .inTable('users')
      .onDelete('CASCADE');
    table.dropIndex(['concept_id', 'bloom_level']);
    table.dropIndex(
      ['concept_id', 'bloom_level', 'difficulty_tier'],
      'idx_questions_tier'
    );
  });
  await knex.raw(`
    CREATE INDEX idx_questions_public_pool
    ON questions (concept_id, bloom_level, difficulty_tier)
    WHERE owner_user_id IS NULL
  `);
  await knex.raw(`
    CREATE INDEX idx_questions_private_pool
    ON questions (owner_user_id, concept_id, bloom_level, difficulty_tier)
    WHERE owner_user_id IS NOT NULL
  `);

  await knex.schema.alterTable('question_serving_log', table => {
    table.dropIndex(['user_id']);
    table.index(['question_id']);
  });
}

export async function down(knex) {
  await knex.schema.alterTable('question_serving_log', table => {
    table.dropIndex(['question_id']);
    table.index(['user_id']);
  });

  await knex.raw('DROP INDEX IF EXISTS idx_questions_public_pool');
  await knex.raw('DROP INDEX IF EXISTS idx_questions_private_pool');
  await knex.schema.alterTable('questions', table => {
    table.index(['concept_id', 'bloom_level']);
    table.index(
      ['concept_id', 'bloom_level', 'difficulty_tier'],
      'idx_questions_tier'
    );
    table.dropForeign(['owner_user_id']);
    table.dropColumn('owner_user_id');
  });
}
