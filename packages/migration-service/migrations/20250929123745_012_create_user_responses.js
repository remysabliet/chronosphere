export async function up(knex) {
  await knex.schema.createTable('user_responses', table => {
    table.uuid('id').primary();
    table.uuid('session_id');
    table.uuid('user_id').notNullable();
    table.uuid('question_id').notNullable();
    table.uuid('concept_id').notNullable();
    table.string('bloom_level').notNullable();
    table.string('selected_option');
    table.boolean('is_correct');
    table.string('confidence_level');
    table.integer('response_time');
    table.string('decision_type');
    table.timestamp('timestamp').notNullable();
    table.string('attempt_quality');
    table.integer('question_sequence_order');

    // Foreign key constraints
    table
      .foreign('session_id')
      .references('session_id')
      .inTable('quiz_sessions')
      .onDelete('SET NULL');
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
    table
      .foreign('concept_id')
      .references('id')
      .inTable('learning_units')
      .onDelete('CASCADE');

    // Indexes
    table.index(['user_id', 'concept_id', 'bloom_level']);
    table.index(['question_id']);
    table.index(['timestamp']);
    table.index(['is_correct']);
    table.index(['decision_type']);
    table.index(['user_id', 'is_correct', 'timestamp']);
    table.index(['session_id']);

    // Check constraints
    table.check('decision_type IN (?, ?, ?, ?)', [
      'Review',
      'Reinforce',
      'Advance',
      'Remediate',
    ]);
    table.check('confidence_level IN (?, ?, ?)', ['Low', 'Medium', 'High']);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('user_responses');
}
