/**
 * user_thema_exposure.timestamp was created notNullable with no DB default,
 * unlike its sibling thema_extraction_inputs.timestamp — any insert that
 * doesn't set it explicitly violates the not-null constraint.
 */
export async function up(knex) {
  await knex.raw(
    'ALTER TABLE user_thema_exposure ALTER COLUMN timestamp SET DEFAULT now()'
  );
}

export async function down(knex) {
  await knex.raw(
    'ALTER TABLE user_thema_exposure ALTER COLUMN timestamp DROP DEFAULT'
  );
}
