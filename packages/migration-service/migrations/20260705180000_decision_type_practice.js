/**
 * Adaptive engine review point 4: exhaustive decision bands. The 'Reinforce'
 * decision type becomes 'Practice' (the 0.40-0.85 band); allowed values are
 * Review / Practice / Advance / Remediate.
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
  await dropCheckConstraintsOn(knex, 'user_responses', 'decision_type');
  await knex('user_responses')
    .where('decision_type', 'Reinforce')
    .update({ decision_type: 'Practice' });
  await knex('learning_path_log')
    .where('decision_type', 'Reinforce')
    .update({ decision_type: 'Practice' });
  await knex('mastery_log')
    .where('decision_type', 'Reinforce')
    .update({ decision_type: 'Practice' });
  await knex.raw(
    "ALTER TABLE user_responses ADD CONSTRAINT chk_user_responses_decision_type CHECK (decision_type IN ('Review', 'Practice', 'Advance', 'Remediate'))"
  );
}

export async function down(knex) {
  await knex.raw(
    'ALTER TABLE user_responses DROP CONSTRAINT IF EXISTS chk_user_responses_decision_type'
  );
  await knex('user_responses')
    .where('decision_type', 'Practice')
    .update({ decision_type: 'Reinforce' });
  await knex('learning_path_log')
    .where('decision_type', 'Practice')
    .update({ decision_type: 'Reinforce' });
  await knex('mastery_log')
    .where('decision_type', 'Practice')
    .update({ decision_type: 'Reinforce' });
  await knex.raw(
    "ALTER TABLE user_responses ADD CONSTRAINT chk_user_responses_decision_type CHECK (decision_type IN ('Review', 'Reinforce', 'Advance', 'Remediate'))"
  );
}
