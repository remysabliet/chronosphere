export async function up(knex) {
  await knex.schema.createTable('question_validation_log', table => {
    table.uuid('id').primary();
    table.uuid('question_id');
    table.string('validation_status').notNullable();
    table.specificType('failed_checks', 'TEXT[]');
    table.timestamp('timestamp').defaultTo(knex.fn.now());
    table.text('notes');
    table.float('validation_score');
    table.string('validator_version');

    // Foreign key constraint
    table
      .foreign('question_id')
      .references('id')
      .inTable('questions')
      .onDelete('CASCADE');

    // Indexes
    table.index(['question_id']);
    table.index(['validation_status']);
    table.index(['timestamp']);

    // Check constraints
    table.check('validation_status IN (?, ?, ?)', [
      'Passed',
      'Failed',
      'Warning',
    ]);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('question_validation_log');
}
