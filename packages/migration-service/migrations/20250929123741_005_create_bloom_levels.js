export async function up(knex) {
  await knex.schema.createTable('bloom_levels', table => {
    table.string('level').primary();
    table.text('description');
    table.integer('order_index');
  });

  // Note: Seed data moved to seeds/001_foundation_data.js
}

export async function down(knex) {
  await knex.schema.dropTable('bloom_levels');
}