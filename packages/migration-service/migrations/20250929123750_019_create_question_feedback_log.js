export async function up(knex) {
  await knex.schema.createTable('question_feedback_log', table => {
    table.uuid('id').primary();
    table.uuid('user_id').notNullable();
    table.uuid('question_id').notNullable();
    table.uuid('response_id').notNullable();
    table.integer('rating');
    table.string('flag_reason');
    table.text('notes');
    table.timestamp('timestamp').defaultTo(knex.fn.now());

    // Foreign key constraints
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
      .foreign('response_id')
      .references('id')
      .inTable('user_responses')
      .onDelete('CASCADE');

    // Indexes
    table.index(['user_id']);
    table.index(['question_id']);
    table.index(['response_id']);
    table.index(['rating']);
    table.index(['flag_reason']);

    // Check constraints
    table.check('rating BETWEEN ? AND ?', [1, 5]);
    table.check('flag_reason IN (?, ?, ?, ?, ?, ?)', [
      'Confusing',
      'Incorrect',
      'Too Easy',
      'Too Hard',
      'Poorly Worded',
      'Technical Error',
    ]);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('question_feedback_log');
}
