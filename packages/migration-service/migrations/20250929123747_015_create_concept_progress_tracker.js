export async function up(knex) {
  await knex.schema.createTable('concept_progress_tracker', table => {
    table.uuid('user_id').notNullable();
    table.uuid('concept_id').notNullable();
    table.string('bloom_level').notNullable();
    table.timestamp('first_attempt');
    table.timestamp('last_attempt');
    table.integer('attempt_count');
    table.integer('correct_count');
    table.integer('slip_count');
    table.string('mastery_status');

    // Primary key
    table.primary(['user_id', 'concept_id', 'bloom_level']);

    // Foreign key constraints
    table
      .foreign('user_id')
      .references('user_id')
      .inTable('users')
      .onDelete('CASCADE');
    table
      .foreign('concept_id')
      .references('id')
      .inTable('learning_units')
      .onDelete('CASCADE');

    // Indexes
    table.index(['user_id', 'concept_id', 'bloom_level']);

    // Check constraints
    table.check('mastery_status IN (?, ?, ?)', [
      'In Progress',
      'Mastered',
      'Expired',
    ]);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('concept_progress_tracker');
}
