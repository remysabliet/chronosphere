export async function up(knex) {
  await knex.schema.createTable('thema_extraction_inputs', table => {
    table.uuid('id').primary().defaultTo(knex.fn.uuid());
    table.uuid('user_id').nullable();
    table.uuid('session_id').nullable();
    table.text('raw_user_input').notNullable();
    table.string('extracted_thema').nullable();
    table.string('extracted_topic').nullable();
    table.string('extraction_model').nullable();
    table.float('extraction_confidence').nullable();
    table.boolean('user_corrected').defaultTo(false);
    table.text('user_correction').nullable();
    table.text('notes').nullable();
    table.timestamp('timestamp').defaultTo(knex.fn.now());

    table
      .foreign('user_id')
      .references('user_id')
      .inTable('users')
      .onDelete('CASCADE');

    table
      .foreign('session_id')
      .references('session_id')
      .inTable('quiz_sessions')
      .onDelete('SET NULL');

    table.index(['user_id']);
    table.index(['session_id']);
    table.index(['extracted_thema', 'extracted_topic']);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('thema_extraction_inputs');
}
