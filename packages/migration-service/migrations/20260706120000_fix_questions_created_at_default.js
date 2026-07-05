/**
 * Same gap as learning_units/user_thema_exposure: created_at was notNullable
 * with no DB default, so any insert that doesn't set it explicitly fails.
 */
export async function up(knex) {
  await knex.schema.alterTable('questions', table => {
    table
      .timestamp('created_at')
      .notNullable()
      .defaultTo(knex.fn.now())
      .alter();
  });
}

export async function down(knex) {
  await knex.schema.alterTable('questions', table => {
    table.timestamp('created_at').notNullable().alter();
  });
}
