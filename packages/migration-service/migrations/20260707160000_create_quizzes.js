/**
 * A quiz is a user-owned configuration (thema + wizard choices), not the
 * questions themselves: questions stay in the shared/private pools and
 * sessions are runs of a quiz. visibility gates future sharing — private
 * quizzes (e.g. built from personal documents) are only ever listed for
 * their owner.
 */
export async function up(knex) {
  await knex.schema.createTable('quizzes', table => {
    table.uuid('id').primary().defaultTo(knex.raw('gen_random_uuid()'));
    table.uuid('owner_user_id').notNullable();
    table.text('thema').notNullable();
    table.text('title').notNullable();
    table.specificType('question_types', 'TEXT[]').notNullable();
    table.integer('question_count');
    table.integer('time_limit_minutes');
    table.text('visibility').notNullable().defaultTo('private');
    table.timestamp('created_at').notNullable().defaultTo(knex.fn.now());
    table.timestamp('updated_at').notNullable().defaultTo(knex.fn.now());

    table
      .foreign('owner_user_id')
      .references('user_id')
      .inTable('users')
      .onDelete('CASCADE');

    table.index(['owner_user_id', 'updated_at'], 'idx_quizzes_owner_recent');
    table.index(['owner_user_id', 'thema'], 'idx_quizzes_owner_thema');
  });

  await knex.raw(`
    ALTER TABLE quizzes ADD CONSTRAINT chk_quizzes_visibility
    CHECK (visibility IN ('private', 'shared', 'public'))
  `);
  await knex.raw(`
    ALTER TABLE quizzes ADD CONSTRAINT chk_quizzes_question_types
    CHECK (
      cardinality(question_types) >= 1
      AND question_types <@ ARRAY['MCQ', 'MCQMultiSelect', 'TrueFalse', 'FillInBlank']::text[]
    )
  `);
  await knex.raw(`
    ALTER TABLE quizzes ADD CONSTRAINT chk_quizzes_has_size
    CHECK (question_count IS NOT NULL OR time_limit_minutes IS NOT NULL)
  `);
}

export async function down(knex) {
  await knex.schema.dropTable('quizzes');
}
