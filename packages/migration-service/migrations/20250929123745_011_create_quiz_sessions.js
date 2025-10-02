export async function up(knex) {
  await knex.schema.createTable('quiz_sessions', table => {
    table.uuid('session_id').primary();
    table.uuid('user_id').notNullable();
    table.string('thema');
    table.string('topic');
    table.string('session_type').defaultTo('learning');
    table.timestamp('start_time').notNullable();
    table.timestamp('end_time');
    table.integer('total_questions').defaultTo(0);
    table.integer('correct_answers').defaultTo(0);
    table.integer('total_time_seconds');
    table.string('session_status').defaultTo('active');
    table.json('difficulty_progression');
    table.json('bloom_level_distribution');
    table.json('session_goals');
    table.float('completion_rate');
    table.float('average_response_time');
    table.json('confidence_trend');
    table.json('mastery_gains');
    table.timestamp('created_at').defaultTo(knex.fn.now());
    table.timestamp('updated_at').defaultTo(knex.fn.now());

    // Foreign key constraint
    table
      .foreign('user_id')
      .references('user_id')
      .inTable('users')
      .onDelete('CASCADE');

    // Indexes
    table.index(['user_id']);
    table.index(['start_time']);
    table.index(['session_status']);
    table.index(['session_type']);

    // Check constraints
    table.check('session_type IN (?, ?, ?)', [
      'learning',
      'review',
      'assessment',
    ]);
    table.check('session_status IN (?, ?, ?)', [
      'active',
      'completed',
      'abandoned',
    ]);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('quiz_sessions');
}
