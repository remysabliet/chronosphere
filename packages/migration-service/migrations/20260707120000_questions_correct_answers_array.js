/**
 * Multi-select questions need more than one correct option, so
 * `correct_answer` (a single string) becomes `correct_answers` (a jsonb
 * array) — every question type stores its answer(s) the same way, a
 * single-answer question is just an array of one.
 */
export async function up(knex) {
  await knex.raw(`
    ALTER TABLE questions
    ALTER COLUMN correct_answer TYPE jsonb
    USING CASE WHEN correct_answer IS NULL THEN NULL ELSE to_jsonb(ARRAY[correct_answer]) END
  `);
  await knex.raw(
    'ALTER TABLE questions RENAME COLUMN correct_answer TO correct_answers'
  );
}

export async function down(knex) {
  await knex.raw(
    'ALTER TABLE questions RENAME COLUMN correct_answers TO correct_answer'
  );
  await knex.raw(`
    ALTER TABLE questions
    ALTER COLUMN correct_answer TYPE varchar
    USING correct_answer ->> 0
  `);
}
