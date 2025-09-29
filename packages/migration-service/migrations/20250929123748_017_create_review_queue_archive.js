export async function up(knex) {
  await knex.schema.createTable('review_queue_archive', table => {
    table.uuid('id').primary();
    table.uuid('user_id').notNullable();
    table.uuid('concept_id').notNullable();
    table.string('bloom_level').notNullable();
    table.uuid('question_id').notNullable();
    table.string('outcome').notNullable();
    table.integer('response_time');
    table.timestamp('timestamp').notNullable();
    table.string('decay_trigger');
    table.string('source');
    table.text('notes');
    table.string('version');
    table.timestamp('archived_at').defaultTo(knex.fn.now());

    // Foreign key constraints
    table.foreign('user_id').references('user_id').inTable('users').onDelete('CASCADE');
    table.foreign('concept_id').references('id').inTable('learning_units').onDelete('CASCADE');
    table.foreign('question_id').references('id').inTable('questions').onDelete('CASCADE');

    // Indexes
    table.index(['user_id', 'concept_id', 'bloom_level']);
    table.index(['timestamp']);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('review_queue_archive');
}