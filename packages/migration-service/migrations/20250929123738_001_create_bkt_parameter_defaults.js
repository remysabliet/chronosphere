export async function up(knex) {
  await knex.schema.createTable('bkt_parameter_defaults', table => {
    table.string('complexity_level').primary();
    table.float('P_T').notNullable();
    table.float('P_L0').defaultTo(0.2);
    table.float('P_G').defaultTo(0.25);
    table.float('P_S').defaultTo(0.1);
  });

  // Note: Seed data moved to seeds/001_foundation_data.js
}

export async function down(knex) {
  await knex.schema.dropTable('bkt_parameter_defaults');
}