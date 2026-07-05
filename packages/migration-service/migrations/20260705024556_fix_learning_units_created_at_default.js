export async function up(knex) {
  await knex.schema.alterTable('learning_units', table => {
    table
      .timestamp('created_at')
      .notNullable()
      .defaultTo(knex.fn.now())
      .alter();
  });
}

export async function down(knex) {
  await knex.schema.alterTable('learning_units', table => {
    table.timestamp('created_at').notNullable().alter();
  });
}
