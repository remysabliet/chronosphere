export async function up(knex) {
  await knex.schema.createTable('user_thema_exposure', table => {
    table.uuid('user_id').notNullable();
    table.string('thema').notNullable();
    table.string('exposure_level').notNullable();
    table.string('source');
    table.timestamp('timestamp').notNullable();
    table.text('notes');

    // Primary key
    table.primary(['user_id', 'thema']);

    // Foreign key constraint
    table.foreign('user_id').references('user_id').inTable('users').onDelete('CASCADE');

    // Indexes
    table.index(['user_id', 'thema']);
    table.index(['timestamp']);

    // Check constraint
    table.check('exposure_level IN (?, ?, ?, ?)', ['Unseen', 'Recognized', 'Practiced', 'Mastered']);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('user_thema_exposure');
}