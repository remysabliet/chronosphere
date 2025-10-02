export async function up(knex) {
  await knex.schema.createTable('irt_guessing_defaults', table => {
    table.string('question_type').primary();
    table.float('guessing_c').notNullable();
  });

  // Note: Seed data moved to seeds/001_foundation_data.js
}

export async function down(knex) {
  await knex.schema.dropTable('irt_guessing_defaults');
}
