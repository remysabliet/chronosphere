export async function up(knex) {
  await knex.schema.createTable('bloom_level_weights', table => {
    table.string('bloom_level').primary();
    table.float('weight').notNullable();
  });

  // Note: Seed data moved to seeds/001_foundation_data.js
}

export async function down(knex) {
  await knex.schema.dropTable('bloom_level_weights');
}
