export async function up(knex) {
  await knex.schema.createTable('users', table => {
    table.uuid('user_id').primary();
    table.string('name');
    table.string('email');
    table.integer('age');
    table.string('profession');
    table.string('education');
    table.uuid('role_id');
    table.boolean('consent_for_personalization').defaultTo(false);
    table.timestamp('personalization_consent_timestamp');
    table.timestamp('created_at').notNullable();
    table.timestamp('last_login_at');
    table.string('language_preference').defaultTo('en');
    table.string('account_status').defaultTo('active');

    // Foreign key constraint
    table.foreign('role_id').references('role_id').inTable('user_roles').onDelete('SET NULL');

    // Indexes
    table.index(['email']);
    table.index(['last_login_at']);
    table.index(['role_id']);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('users');
}