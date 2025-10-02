export async function up(knex) {
  await knex.schema.createTable('mastery_log', table => {
    table.uuid('user_id').notNullable();
    table.uuid('concept_id').notNullable();
    table.string('bloom_level').notNullable();
    table.string('thema').notNullable();
    table.string('topic');
    table.timestamp('mastery_date').notNullable();
    table.float('P_Ln_at_mastery').notNullable();
    table.float('theta_at_mastery').notNullable();
    table.specificType('bloom_levels_assessed', 'TEXT[]').notNullable();
    table.integer('slip_count_recent').defaultTo(0);
    table.string('decision_type').notNullable();
    table.text('feedback_text');
    table.timestamp('last_reinforced');
    table.integer('decay_threshold_days').defaultTo(14);
    table.string('decay_status').defaultTo('Active');
    table.string('mastery_status').defaultTo('In Progress');
    table.integer('review_count').defaultTo(0);
    table.string('last_review_outcome');
    table.float('slip_rate').defaultTo(0.0);
    table.string('version');
    table.string('author').defaultTo('AI-generated');
    table.float('decay_magnitude');
    table.date('last_decay_applied_at');
    table.json('usage_stats');

    // Primary key
    table.primary(['user_id', 'concept_id', 'bloom_level']);

    // Foreign key constraints
    table
      .foreign('user_id')
      .references('user_id')
      .inTable('users')
      .onDelete('CASCADE');
    table
      .foreign('concept_id')
      .references('id')
      .inTable('learning_units')
      .onDelete('CASCADE');

    // Indexes
    table.index(['user_id', 'concept_id', 'bloom_level']);
    table.index(['decay_status']);
    table.index(['last_decay_applied_at']);
    table.index(['decay_status', 'last_reinforced']);

    // Check constraints
    table.check('decay_status IN (?, ?, ?)', [
      'Active',
      'Expired',
      'Pending review',
    ]);
    table.check('mastery_status IN (?, ?, ?)', [
      'In Progress',
      'Mastered',
      'Expired',
    ]);
  });
}

export async function down(knex) {
  await knex.schema.dropTable('mastery_log');
}
