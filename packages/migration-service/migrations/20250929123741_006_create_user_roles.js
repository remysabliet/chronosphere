export async function up(knex) {
  await knex.schema.createTable('user_roles', table => {
    table.uuid('role_id').primary();
    table.string('role_name').notNullable().unique();
    table.text('description');
    table.json('permissions');
    table.timestamp('created_at').defaultTo(knex.fn.now());
    table.boolean('is_active').defaultTo(true);

    // Indexes
    table.index(['role_name']);
    table.index(['is_active']);

    // Check constraint
    table.check('role_name IN (?, ?, ?, ?, ?)', ['learner', 'admin', 'moderator', 'content_creator', 'analyst']);
  });

  // Note: Seed data should be in separate seed files, not migrations
}

export async function down(knex) {
  await knex.schema.dropTable('user_roles');
}