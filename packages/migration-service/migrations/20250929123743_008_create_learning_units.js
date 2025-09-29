export async function up(knex) {
  await knex.schema.createTable('learning_units', table => {
    table.uuid('id').primary();
    table.string('thema').notNullable();
    table.string('topic');
    table.string('concept_name').notNullable();
    table.text('learning_goal');
    table.specificType('bloom_levels_supported', 'TEXT[]');
    table.integer('estimated_time_minutes');
    table.integer('bloom_coverage_score');
    table.string('complexity_level');
    table.string('created_by');
    table.timestamp('created_at').notNullable();
    table.string('author');
    table.string('version');

    // Foreign key constraint
    table.foreign('complexity_level').references('complexity_level').inTable('bkt_parameter_defaults');

    // Indexes
    table.index(['thema', 'topic']);
    table.index(['concept_name']);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('learning_units');
}