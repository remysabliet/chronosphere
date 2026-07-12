/**
 * selected_option stores JSON-encoded selected answer(s) (see
 * SessionService.submit_answer). For multi-select questions with several
 * verbose options, that easily exceeds varchar(255) and the insert fails
 * outright (StringDataRightTruncationError) — discovered by actually driving
 * a real quiz session end to end. Widening to TEXT on the partitioned parent
 * propagates to every partition automatically (PG 11+).
 */
export async function up(knex) {
  await knex.raw(
    'ALTER TABLE user_responses ALTER COLUMN selected_option TYPE TEXT'
  );
}

export async function down(knex) {
  await knex.raw(
    'ALTER TABLE user_responses ALTER COLUMN selected_option TYPE VARCHAR(255)'
  );
}
