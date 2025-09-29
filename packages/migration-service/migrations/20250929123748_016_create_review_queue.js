export async function up(knex) {
  await knex.schema.createTable('review_queue', table => {
    table.uuid('user_id').notNullable();
    table.uuid('concept_id').notNullable();
    table.string('bloom_level').notNullable();
    table.uuid('question_id');
    table.string('outcome');
    table.integer('response_time');
    table.timestamp('timestamp').notNullable();

    // Primary key
    table.primary(['user_id', 'concept_id', 'bloom_level']);

    // Foreign key constraints
    table.foreign('user_id').references('user_id').inTable('users').onDelete('CASCADE');
    table.foreign('concept_id').references('id').inTable('learning_units').onDelete('CASCADE');
    table.foreign('question_id').references('id').inTable('questions').onDelete('SET NULL');

    // Indexes
    table.index(['user_id', 'concept_id', 'bloom_level']);
    table.index(['timestamp']);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('review_queue');
}