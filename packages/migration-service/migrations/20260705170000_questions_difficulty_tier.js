/**
 * Adaptive engine review point 3: LLM-assigned IRT item parameters (a/b/c)
 * are uncalibratable guesses. Replace with a coarse difficulty_tier label;
 * generator labeling accuracy is monitored via user_responses correct rates.
 */
export async function up(knex) {
  await knex.schema.alterTable('questions', table => {
    table.dropIndex(['difficulty_b']);
    table.dropColumn('difficulty_b');
    table.dropColumn('discrimination_a');
    table.dropColumn('guessing_c');
    table.string('difficulty_tier').notNullable().defaultTo('medium');
    table.index(
      ['concept_id', 'bloom_level', 'difficulty_tier'],
      'idx_questions_tier'
    );
  });
  await knex.raw(
    "ALTER TABLE questions ADD CONSTRAINT chk_questions_difficulty_tier CHECK (difficulty_tier IN ('easy', 'medium', 'hard'))"
  );

  await knex.schema.dropTableIfExists('irt_bloom_defaults');
  await knex.schema.dropTableIfExists('irt_guessing_defaults');
}

export async function down(knex) {
  await knex.schema.createTable('irt_bloom_defaults', table => {
    table.string('bloom_level').primary();
    table.float('difficulty_b_min').notNullable();
    table.float('difficulty_b_max').notNullable();
    table.float('discrimination_a_min').notNullable();
    table.float('discrimination_a_max').notNullable();
  });
  await knex.schema.createTable('irt_guessing_defaults', table => {
    table.string('question_type').primary();
    table.float('guessing_c').notNullable();
  });

  await knex.raw(
    'ALTER TABLE questions DROP CONSTRAINT IF EXISTS chk_questions_difficulty_tier'
  );
  await knex.schema.alterTable('questions', table => {
    table.dropIndex(
      ['concept_id', 'bloom_level', 'difficulty_tier'],
      'idx_questions_tier'
    );
    table.dropColumn('difficulty_tier');
    table.float('difficulty_b');
    table.float('discrimination_a');
    table.float('guessing_c');
    table.index(['difficulty_b']);
  });
}
