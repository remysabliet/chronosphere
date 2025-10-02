export async function up(knex) {
  await knex.schema.createTable('questions', table => {
    table.uuid('id').primary();
    table.uuid('concept_id').notNullable();
    table.string('bloom_level').notNullable();
    table.float('difficulty_b');
    table.float('discrimination_a');
    table.float('guessing_c');
    table.string('question_type');
    table.text('question_text').notNullable();
    table.json('options');
    table.string('correct_answer');
    table.text('explanation');
    table.string('estimated_time');
    table.specificType('tags', 'TEXT[]');
    table.string('language');
    table.string('source');
    table.string('version');
    table.string('created_by');
    table.timestamp('created_at').notNullable();

    // Foreign key constraint
    table
      .foreign('concept_id')
      .references('id')
      .inTable('learning_units')
      .onDelete('CASCADE');

    // Indexes
    table.index(['concept_id', 'bloom_level']);
    table.index(['difficulty_b']);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('questions');
}
