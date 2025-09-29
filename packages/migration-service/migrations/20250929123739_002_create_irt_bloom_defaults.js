export async function up(knex) {
  await knex.schema.createTable('irt_bloom_defaults', table => {
    table.string('bloom_level').primary();
    table.float('difficulty_b_min').notNullable();
    table.float('difficulty_b_max').notNullable();
    table.float('discrimination_a_min').notNullable();
    table.float('discrimination_a_max').notNullable();
  });

  // Note: Seed data moved to seeds/001_foundation_data.js
}

export async function down(knex) {
  await knex.schema.dropTable('irt_bloom_defaults');
}