export async function up(knex) {
  await knex.schema.createTable('learning_path_log', table => {
    table.uuid('user_id').notNullable();
    table.uuid('concept_id').notNullable();
    table.string('bloom_level').notNullable();
    table.string('decision_type');
    table.timestamp('timestamp').notNullable();
    table.string('triggered_by');

    // Foreign key constraints
    table.foreign('user_id').references('user_id').inTable('users').onDelete('CASCADE');
    table.foreign('concept_id').references('id').inTable('learning_units').onDelete('CASCADE');
  });
}

export async function down(knex) {
  await knex.schema.dropTable('learning_path_log');
}