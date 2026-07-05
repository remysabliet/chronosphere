/**
 * Adaptive engine review point 6: one scheduler (FSRS) replaces the three
 * forgetting mechanisms (SM-2 intervals, apply_decay job, decay_status flags).
 * FSRS predicted recall is the single decay signal.
 */

const dropCheckConstraintsOn = async (knex, tableName, columnName) => {
  const rows = await knex('pg_constraint as c')
    .join('pg_class as t', 'c.conrelid', 't.oid')
    .where('t.relname', tableName)
    .andWhere('c.contype', 'c')
    .whereRaw('pg_get_constraintdef(c.oid) ILIKE ?', [`%${columnName}%`])
    .select('c.conname');
  for (const row of rows) {
    await knex.raw('ALTER TABLE ?? DROP CONSTRAINT IF EXISTS ??', [
      tableName,
      row.conname,
    ]);
  }
};

export async function up(knex) {
  await dropCheckConstraintsOn(knex, 'mastery_log', 'decay_status');
  await knex.schema.alterTable('mastery_log', table => {
    table.dropIndex(['decay_status']);
    table.dropIndex(['last_decay_applied_at']);
    table.dropIndex(['decay_status', 'last_reinforced']);
    table.dropColumn('decay_threshold_days');
    table.dropColumn('decay_status');
    table.dropColumn('decay_magnitude');
    table.dropColumn('last_decay_applied_at');
    table.json('fsrs_state');
    table.timestamp('next_review_at');
    table.index(['user_id', 'next_review_at'], 'idx_mastery_log_next_review');
  });

  await knex.schema.alterTable('review_queue_archive', table => {
    table.renameColumn('decay_trigger', 'review_trigger');
  });
}

export async function down(knex) {
  await knex.schema.alterTable('review_queue_archive', table => {
    table.renameColumn('review_trigger', 'decay_trigger');
  });

  await knex.schema.alterTable('mastery_log', table => {
    table.dropIndex(
      ['user_id', 'next_review_at'],
      'idx_mastery_log_next_review'
    );
    table.dropColumn('fsrs_state');
    table.dropColumn('next_review_at');
    table.integer('decay_threshold_days').defaultTo(14);
    table.string('decay_status').defaultTo('Active');
    table.float('decay_magnitude');
    table.date('last_decay_applied_at');
    table.index(['decay_status']);
    table.index(['last_decay_applied_at']);
    table.index(['decay_status', 'last_reinforced']);
  });
  await knex.raw(
    "ALTER TABLE mastery_log ADD CONSTRAINT chk_mastery_log_decay_status CHECK (decay_status IN ('Active', 'Expired', 'Pending review'))"
  );
}
